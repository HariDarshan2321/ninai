from dataclasses import replace
from datetime import datetime, timezone
from email.message import Message
import io
import json
import unittest
from urllib.error import HTTPError

from ninai_cloud.team_github import GitHubSourceVerifier, GitHubUserGrant
from ninai_cloud.team_sources import SourceRequest, SourceStatus, parse_source_reference, proof_status


REFERENCE = parse_source_reference("https://github.com/synthetic/payments/pull/37")
OWNER_TOKEN = "ghu_ownerSynthetic"
MEMBER_TOKEN = "ghu_memberSynthetic"
PULL_PATH = "https://api.github.com/repos/synthetic/payments/pulls/37"


class Response(io.BytesIO):
    def __init__(self, url, payload, *, status=200, content_type="application/json", encoding="identity"):
        super().__init__(json.dumps(payload).encode())
        self.url, self.status = url, status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["Content-Encoding"] = encoding

    def geturl(self):
        return self.url


class FixtureGitHub:
    def __init__(self):
        self.pulls = {
            "base": {"repo": {"full_name": "Synthetic/Payments"}},
            "head": {"sha": "a" * 40},
            "number": 37,
            "node_id": "PR_synthetic37",
            "title": "Synthetic refund",
            "body": "A refund needs an idempotency key.",
        }
        self.identities = {OWNER_TOKEN: 123, MEMBER_TOKEN: 456}
        self.denied_tokens = set()
        self.requests = []
        self.response_options = {}

    def open(self, request, *, timeout):
        token = request.get_header("Authorization").removeprefix("Bearer ")
        self.requests.append((request.full_url, token))
        if timeout <= 0 or timeout > 1.25:
            raise AssertionError("Unexpected GitHub deadline")
        if request.full_url == "https://api.github.com/user":
            return Response(request.full_url, {"id": self.identities[token]})
        if request.full_url != PULL_PATH:
            raise AssertionError("Unexpected GitHub request path")
        if token in self.denied_tokens:
            raise HTTPError(request.full_url, 404, "Not Found", {}, io.BytesIO())
        options = self.response_options
        return Response(options.get("url", request.full_url), self.pulls,
                        **{key: value for key, value in options.items() if key != "url"})


class GitHubSourceTests(unittest.TestCase):
    def setUp(self):
        self.github = FixtureGitHub()
        self.grants = {
            "owner": GitHubUserGrant(123, OWNER_TOKEN),
            "member": GitHubUserGrant(456, MEMBER_TOKEN),
        }
        self.verifier = GitHubSourceVerifier(self.grant_for, opener=self.github)
        self.request = SourceRequest("fixture-workspace", "fixture-project", "owner", None,
                                     1, REFERENCE, None, "fixture-review")

    def grant_for(self, request):
        if (request.workspace_id, request.project_id) == ("fixture-workspace", "fixture-project"):
            return self.grants.get(request.user_id)

    def test_verify_two_users_and_fail_closed_after_one_loses_access(self):
        proof = self.verifier.verify(self.request)
        self.assertIsNotNone(proof)
        owner = replace(self.request, expected_fingerprint=proof.fingerprint, request_id="fixture-read")
        member = replace(owner, user_id="member", request_id="fixture-member-read")
        self.assertEqual(proof_status(member, self.verifier.verify(member), now=datetime.now(timezone.utc)),
                         SourceStatus.VERIFIED)
        self.github.denied_tokens.add(MEMBER_TOKEN)
        self.assertIsNone(self.verifier.verify(member))
        self.assertEqual(proof_status(owner, self.verifier.verify(owner), now=datetime.now(timezone.utc)),
                         SourceStatus.VERIFIED)

    def test_cross_scope_wrong_identity_and_installation_credentials_do_not_read_pull(self):
        self.assertIsNone(self.verifier.verify(replace(self.request, project_id="elsewhere")))
        self.grants["owner"] = GitHubUserGrant(123, "ghs_installationSynthetic")
        self.assertIsNone(self.verifier.verify(self.request))
        self.assertEqual(self.github.requests, [])
        self.grants["owner"] = GitHubUserGrant(123, MEMBER_TOKEN)
        self.assertIsNone(self.verifier.verify(self.request))
        self.assertEqual(self.github.requests, [("https://api.github.com/user", MEMBER_TOKEN)])

    def test_only_canonical_reference_and_exact_response_are_accepted(self):
        self.assertIsNone(self.verifier.verify(replace(self.request, reference=replace(
            REFERENCE, canonical_url="https://other.example.invalid/synthetic/payments/pull/37"))))
        self.assertEqual(self.github.requests, [])
        self.github.pulls["number"] = 38
        self.assertIsNone(self.verifier.verify(self.request))
        self.github.pulls["number"] = 37
        self.github.pulls["base"]["repo"]["full_name"] = "other/payments"
        self.assertIsNone(self.verifier.verify(self.request))

    def test_redirect_encoded_and_oversized_responses_supply_no_proof(self):
        for options in (
            {"status": 302}, {"url": "https://elsewhere.example.invalid"},
            {"content_type": "text/html"}, {"encoding": "gzip"},
        ):
            with self.subTest(options=options):
                self.github.response_options = options
                self.assertIsNone(self.verifier.verify(self.request))
        self.github.response_options = {}
        self.github.pulls["body"] = "A" * (512 * 1024)
        self.assertIsNone(self.verifier.verify(self.request))

    def test_editing_evidence_changes_fingerprint(self):
        proof = self.verifier.verify(self.request)
        self.assertIsNotNone(proof)
        request = replace(self.request, expected_fingerprint=proof.fingerprint)
        self.github.pulls["body"] = "This evidence changed."
        status = proof_status(request, self.verifier.verify(request), now=datetime.now(timezone.utc))
        self.assertEqual(status, SourceStatus.CHANGED)
