"""Owner approval must fail closed without a fresh successful OS evaluation."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from ninai.owner_verification import (
    METHOD, OwnerVerificationError, check_owner_verification, verify_owner,
)


class OwnerVerificationTests(unittest.TestCase):
    def setUp(self):
        for target, value in [
            ("ninai.owner_verification.sys.platform", "darwin"),
            ("ninai.owner_verification._HELPER", Path("/bundled/ninai/native/ninai-owner-auth")),
        ]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.file = patch("ninai.owner_verification.Path.is_file", return_value=True).start()
        self.access = patch("ninai.owner_verification.os.access", return_value=True).start()
        self.run = patch("ninai.owner_verification.subprocess.run").start()
        self.addCleanup(patch.stopall)

    def respond(self, verified=True, **fields):
        def result(args, **kwargs):
            request = json.loads(kwargs["input"])
            response = {"method": METHOD, "verified": verified,
                        "nonce": request["nonce"], "os_user_id": os.getuid()}
            response.update(fields)
            return subprocess.CompletedProcess(args, 0, json.dumps(response), "")
        self.run.side_effect = result

    def test_success_returns_fresh_os_account_assertion(self):
        self.respond()
        assertion = verify_owner("approve access to Research for Codex")
        self.assertEqual(assertion.method, METHOD)
        self.assertEqual(assertion.os_user_id, os.getuid())
        self.assertTrue(assertion.verified_at.endswith("+00:00"))
        self.assertEqual(self.run.call_args.args[0], ["/bundled/ninai/native/ninai-owner-auth", "--verify"])
        self.assertEqual(self.run.call_args.kwargs["timeout"], 65)

    def test_each_approval_uses_new_challenge(self):
        self.respond()
        verify_owner("approve first request")
        verify_owner("approve second request")
        nonces = [json.loads(call.kwargs["input"])["nonce"] for call in self.run.call_args_list]
        self.assertNotEqual(*nonces)

    def test_unsupported_platform_never_spawns_helper(self):
        with patch("ninai.owner_verification.sys.platform", "win32"):
            with self.assertRaises(OwnerVerificationError):
                verify_owner("approve access")
        self.run.assert_not_called()

    def test_missing_helper_never_spawns(self):
        self.file.return_value = False
        with self.assertRaises(OwnerVerificationError):
            verify_owner("approve access")
        self.run.assert_not_called()

    def test_environment_cannot_select_helper_or_inject_dylib(self):
        self.respond()
        with patch.dict(os.environ, {"NINAI_OWNER_AUTH_HELPER": "/tmp/fake", "DYLD_INSERT_LIBRARIES": "/tmp/fake.dylib"}):
            verify_owner("approve access")
        self.assertEqual(self.run.call_args.args[0][0], "/bundled/ninai/native/ninai-owner-auth")
        self.assertNotIn("DYLD_INSERT_LIBRARIES", self.run.call_args.kwargs["env"])

    def test_forged_or_unsuccessful_response_cannot_verify(self):
        for fields in [{"verified": False}, {"verified": 1}, {"nonce": "stale"},
                       {"os_user_id": os.getuid() + 1}, {"os_user_id": str(os.getuid())},
                       {"method": "pin_confirmation"}]:
            with self.subTest(fields=fields):
                self.respond(**fields)
                with self.assertRaises(OwnerVerificationError):
                    verify_owner("approve access")

    def test_failure_exit_overrides_success_payload(self):
        self.run.return_value = subprocess.CompletedProcess([], 1, json.dumps({"method": METHOD, "verified": True, "reason": "cancelled"}), "private OS error")
        with self.assertRaisesRegex(OwnerVerificationError, "cancelled"):
            verify_owner("approve access")

    def test_timeout_or_execution_failure(self):
        for failure in [subprocess.TimeoutExpired("helper", 65), OSError("private details")]:
            with self.subTest(failure=failure):
                self.run.side_effect = failure
                with self.assertRaises(OwnerVerificationError):
                    verify_owner("approve access")

    def test_malformed_response_fails_closed(self):
        for body in ["garbage", "[]", "null", "{}"]:
            self.run.return_value = subprocess.CompletedProcess([], 0, body, "")
            with self.assertRaises(OwnerVerificationError):
                verify_owner("approve access")

    def test_invalid_reason_never_spawns(self):
        for reason in [None, "", " ", "a" * 501, "two\nlines", "null\x00byte"]:
            with self.subTest(reason=reason):
                with self.assertRaises(OwnerVerificationError):
                    verify_owner(reason)
        self.run.assert_not_called()

    def test_preflight_only_uses_check_and_cannot_verify(self):
        self.run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"method": METHOD, "available": True}), "")
        self.assertTrue(check_owner_verification()["available"])
        self.assertEqual(self.run.call_args.args[0][-1], "--check")
        with self.assertRaises(OwnerVerificationError):
            verify_owner("approve access")

    def test_preflight_unavailable_is_explicit(self):
        self.run.return_value = subprocess.CompletedProcess([], 1, json.dumps({"method": METHOD, "available": False, "reason": "unavailable"}), "")
        result = check_owner_verification()
        self.assertFalse(result["available"])
        self.assertIn("unavailable", result["reason"])


if __name__ == "__main__":
    unittest.main()
