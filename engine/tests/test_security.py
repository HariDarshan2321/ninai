from __future__ import annotations

import unittest

from ninai.security import contains_secret, redact_secrets


class SecurityFilterTest(unittest.TestCase):
    # Realistic (non-live) credential shapes that must be caught. The values are
    # assembled from fragments at runtime so no complete credential literal
    # appears in this source file — that keeps GitHub push-protection / secret
    # scanning from flagging the deliberately realistic test fixtures while the
    # assembled string still exercises the detection regexes.
    SECRETS = {
        "aws_access_key": "AKIA" + "IOSFODNN7EXAMPLE",
        "google_api_key": "AIza" + "SyB1234567890abcdefghijklmnopqrstuv",
        "github_fine_grained_pat": "github_" + "pat_11ABCDEFG0123456789_abcdefghijklmnopqrstuvwxyz012345",
        "slack_bot_token": "xox" + "b-1234567890-0987654321-abcdefghijklmnop",
        "stripe_live_key": "sk" + "_live_" + "51H8xABCDEFGHIJKLMNOPQRST",
        "jwt": "eyJ" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkwIn0" + "." + "dozjgNryP4J3jVmNHl0w5N",
        "db_url_password": "postgres://admin:" + "SuperSecret123" + "@db.example.com:5432/prod",
        "generic_password": "password=" + "Hunter2Hunter2Hunter2",
        "db_password_env": "DB_PASSWORD=" + "MyLongSecretValue123",
        "private_key": "-----BEGIN PRIVATE KEY-----\n" + "MIIBVwIBADANBgkq",
        "bearer_token": "Bearer " + "abcdefghijklmnopqrstuvwxyz0123456789",
    }

    def test_secrets_are_detected(self) -> None:
        for name, secret in self.SECRETS.items():
            with self.subTest(secret=name):
                self.assertTrue(
                    contains_secret(secret),
                    f"expected {name} to be detected as a secret",
                )

    def test_secrets_are_redacted(self) -> None:
        for name, secret in self.SECRETS.items():
            with self.subTest(secret=name):
                redacted = redact_secrets(secret)
                self.assertIn("[REDACTED_SECRET]", redacted)

    def test_ordinary_durable_text_is_not_flagged(self) -> None:
        safe = [
            "Finish the Ninai permission dashboard before launch",
            "Priya is waiting for the deck by Thursday",
            "Decided to ship the local MCP server first",
            "The meeting moved to 2pm on the calendar",
        ]
        for text in safe:
            with self.subTest(text=text):
                self.assertFalse(contains_secret(text))


if __name__ == "__main__":
    unittest.main()
