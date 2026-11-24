import asyncio
import json
import unittest

import httpx
from mcp.shared.memory import create_connected_server_and_client_session

from ninai_cloud.team_client import TeamClient, create_stdio_bridge


WORKSPACE = "f42502c2-855b-4c13-999e-1d73df627e29"
PROJECT = "1abf6c7e-6b12-47bd-9c3d-5eaee8eae9c9"
TOKEN = "x" * 43
ORIGIN = "https://ninai.example.invalid"
ENDPOINT = f"{ORIGIN}/api/team-assistant/{WORKSPACE}/projects/{PROJECT}/context"


def client_for(handler, **kwargs):
    return TeamClient(ORIGIN, WORKSPACE, PROJECT, TOKEN, transport=httpx.MockTransport(handler), **kwargs)


class TeamClientConfigTests(unittest.TestCase):
    def test_environment_requires_valid_origin_workspaces_and_token(self):
        values = {"NINAI_TEAM_ORIGIN": ORIGIN, "NINAI_TEAM_WORKSPACE": WORKSPACE,
                  "NINAI_TEAM_PROJECT": PROJECT, "NINAI_TEAM_TOKEN": TOKEN}
        self.assertNotIn(TOKEN, repr(TeamClient.from_environment(values)))
        for field, invalid in (
            ("NINAI_TEAM_ORIGIN", "http://127.0.0.1:8000"),
            ("NINAI_TEAM_ORIGIN", f"{ORIGIN}/mcp"),
            ("NINAI_TEAM_ORIGIN", f"{ORIGIN}?name=team"),
            ("NINAI_TEAM_ORIGIN", "https://person@ninai.example.invalid"),
            ("NINAI_TEAM_ORIGIN", "https://ninai.example.invalid:99999"),
            ("NINAI_TEAM_WORKSPACE", "workspace"),
            ("NINAI_TEAM_PROJECT", "project"),
            ("NINAI_TEAM_TOKEN", "invalid credential"),
        ):
            with self.subTest(field=field, value=invalid), self.assertRaises(ValueError) as error:
                TeamClient.from_environment({**values, field: invalid})
            self.assertNotIn(TOKEN, str(error.exception))

    def test_test_transport_can_allow_only_numeric_loopback_http(self):
        transport = httpx.MockTransport(lambda _: httpx.Response(204))
        TeamClient("http://127.0.0.1:8000", WORKSPACE, PROJECT, TOKEN,
                   transport=transport, allow_loopback_http=True)
        with self.assertRaises(ValueError):
            TeamClient("http://ninai.example.invalid", WORKSPACE, PROJECT, TOKEN,
                       transport=transport, allow_loopback_http=True)


class TeamClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_routes_fixed_project_and_preserves_output_bytes(self):
        exact_packet = '{"outcome":"packet", "current":[{"rule":"Confirm café amount"}]}'

        def server(request):
            self.assertEqual(str(request.url), ENDPOINT)
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.headers.get("authorization"), f"Bearer {TOKEN}")
            self.assertEqual(request.headers.get("accept-encoding"), "identity")
            self.assertEqual(json.loads(request.content), {
                "task": "confirm the café amount", "paths": ["payments:src/refunds.py"], "max_items": 1,
                "max_tokens": len(exact_packet.encode("utf-8")), "history_only": False,
            })
            return httpx.Response(200, content=exact_packet, headers={"Content-Type": "application/json"})

        result = await client_for(server).context("confirm the café amount", ["payments:src/refunds.py"], 1,
                                                   len(exact_packet.encode("utf-8")))
        self.assertFalse(result.isError)
        self.assertEqual([item.text for item in result.content], [exact_packet])
        self.assertIsNone(result.structuredContent)

    async def test_no_content_response_preserves_safe_outcome_without_adding_context(self):
        def server(_):
            return httpx.Response(204, headers={"X-Ninai-Outcome": "conflict",
                                               "X-Ninai-Signals": "resolve-before-edit,budget-exhausted"})

        result = await client_for(server).context("refund retries", max_tokens=1)
        self.assertFalse(result.isError)
        self.assertEqual(result.content, [])
        self.assertEqual(result.model_dump(by_alias=True)["_meta"], {
            "ninai/outcome": "conflict", "ninai/signals": ["resolve-before-edit", "budget-exhausted"],
        })

    async def test_unrecognized_no_content_header_is_not_released(self):
        result = await client_for(lambda _: httpx.Response(
            204, headers={"X-Ninai-Outcome": "empty", "X-Ninai-Signals": TOKEN},
        )).context("refund retries")
        self.assertTrue(result.isError)
        self.assertNotIn(TOKEN, result.model_dump_json())

    async def test_permission_denials_conceal_the_service_response(self):
        for status in (401, 403, 404):
            with self.subTest(status=status):
                client = client_for(lambda _: httpx.Response(status, text=f"service internals: {TOKEN}"))
                result = await client.context("refund retries")
                self.assertTrue(result.isError)
                self.assertEqual([item.text for item in result.content], ["Team access is unavailable."])

    async def test_redirect_is_never_followed(self):
        called = []

        def server(request):
            called.append(str(request.url))
            return httpx.Response(307, headers={"Location": "https://another.example.invalid/context"})

        result = await client_for(server).context("refund retries")
        self.assertTrue(result.isError)
        self.assertEqual(called, [ENDPOINT])

    async def test_unexpected_content_encoding_and_oversize_item_count_are_rejected(self):
        for response in (
            httpx.Response(200, headers={"Content-Type": "application/json", "Content-Encoding": "gzip"}),
            httpx.Response(200, json={"outcome": "packet", "current": [{}], "lineage": [{}]}),
            httpx.Response(200, json={"outcome": "unexpected", "claims": [TOKEN]}),
            httpx.Response(200, content='{"outcome":"empty","outcome":"packet"}',
                           headers={"Content-Type": "application/json"}),
        ):
            result = await client_for(lambda _: response).context("refund retries", max_items=1)
            self.assertTrue(result.isError)
            self.assertNotIn(TOKEN, result.model_dump_json())

    async def test_stream_stops_at_budget(self):
        class OverBudget(httpx.AsyncByteStream):
            closed = False

            async def __aiter__(self):
                yield b"x" * 21
                raise AssertionError("Oversize response was read beyond the first chunk")

            async def aclose(self):
                self.closed = True

        stream = OverBudget()
        result = await client_for(lambda _: httpx.Response(
            200, headers={"Content-Type": "application/json"}, stream=stream,
        )).context("refund retries", max_tokens=20)
        self.assertTrue(result.isError)
        self.assertTrue(stream.closed)

    async def test_timeout_and_invalid_local_requests_are_generic(self):
        called = []

        async def server(request):
            called.append(request)
            await asyncio.sleep(1)

        client = client_for(server, timeout=0.01)
        invalid = await client.context("  ")
        self.assertEqual(called, [])
        self.assertEqual([item.text for item in invalid.content], ["Invalid team context request."])
        timed_out = await client.context("refund retries")
        self.assertEqual(len(called), 1)
        self.assertTrue(timed_out.isError)
        self.assertEqual([item.text for item in timed_out.content], ["Team context service is unavailable."])

    async def test_mcp_protocol_exposes_one_scoped_tool_and_one_text_block(self):
        def server(request):
            if json.loads(request.content)["max_tokens"] == 1:
                return httpx.Response(204, headers={"X-Ninai-Outcome": "empty"})
            return httpx.Response(200, json={"outcome": "empty"})

        bridge = create_stdio_bridge(client_for(server))
        async with create_connected_server_and_client_session(bridge) as session:
            tools = await session.list_tools()
            self.assertEqual([tool.name for tool in tools.tools], ["team_context"])
            self.assertNotIn("token", tools.tools[0].inputSchema["properties"])
            self.assertNotIn("origin", tools.tools[0].inputSchema["properties"])
            result = await session.call_tool("team_context", {"task": "refund retries"})
            self.assertFalse(result.isError)
            self.assertEqual([item.text for item in result.content], ['{"outcome":"empty"}'])
            self.assertIsNone(result.structuredContent)
            small_result = await session.call_tool("team_context", {"task": "refund retries", "max_tokens": 1})
            self.assertEqual(small_result.content, [])
            self.assertEqual(small_result.model_dump(by_alias=True)["_meta"]["ninai/outcome"], "empty")
