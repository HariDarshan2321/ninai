from __future__ import annotations

import sys
import unittest
import asyncio
import hashlib
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.auth import (
    AuthSettings, AuthenticationError, BearerAuthenticator, JWTValidator, MCPTokenVerifier,
    PrincipalResolver,
    PATTokenVerifier, auth_mode,
)


class FakeResult:
    def __init__(self, row): self.row = row
    def fetchone(self): return self.row


class FakeDb:
    def __init__(self, row=(1,)): self.row, self.params = row, None
    def execute(self, _sql, params): self.params = params; return FakeResult(self.row)


class PATFakeDb:
    def __init__(self, row): self.row, self.calls = row, []
    def execute(self, sql, params):
        self.calls.append((sql, params))
        return FakeResult(self.row if sql.lstrip().startswith("SELECT") else None)


class FakeValidator:
    def __init__(self, claims): self.claims, self.token = claims, None
    def validate(self, token): self.token = token; return self.claims


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.settings = AuthSettings(
            issuer="https://issuer.test", audience="ninai", resource="https://api.test/mcp",
            jwks_uri="https://issuer.test/jwks",
        )
        self.claims = {
            "sub": "user-1", "ninai_workspace_id": "workspace-1",
            "ninai_client_connection_id": "client-1",
        }

    def resolver(self, row=(1,)):
        db = FakeDb(row)
        @contextmanager
        def connect(): yield db
        return PrincipalResolver(connect, self.settings), db

    def test_metadata_points_to_external_issuer(self):
        metadata = self.settings.protected_resource_metadata()
        self.assertEqual(metadata["resource"], "https://api.test/mcp")
        self.assertEqual(metadata["authorization_servers"], ["https://issuer.test"])
        self.assertEqual(self.settings.authorization_server_metadata()["jwks_uri"], "https://issuer.test/jwks")

    def test_principal_comes_only_from_signed_claims_and_is_checked_live(self):
        resolver, db = self.resolver()
        principal = resolver.resolve(self.claims)
        self.assertEqual(principal.user_id, "user-1")
        self.assertEqual(principal.workspace_id, "workspace-1")
        self.assertEqual(db.params, ("user-1", "client-1", "workspace-1", "user-1"))

    def test_revoked_client_is_rejected(self):
        resolver, _ = self.resolver(None)
        with self.assertRaisesRegex(AuthenticationError, "revoked or unknown"):
            resolver.resolve(self.claims)

    def test_missing_identity_claim_is_rejected(self):
        resolver, _ = self.resolver()
        with self.assertRaisesRegex(AuthenticationError, "identity claims"):
            resolver.resolve({"sub": "user-1"})

    def test_bearer_header_is_required(self):
        resolver, _ = self.resolver()
        auth = BearerAuthenticator(FakeValidator(self.claims), resolver)
        with self.assertRaisesRegex(AuthenticationError, "Bearer"):
            auth.authenticate("Basic abc")
        principal = auth.authenticate("Bearer signed.jwt")
        self.assertEqual(principal.client_connection_id, "client-1")

    def test_mcp_verifier_returns_trusted_principal_claims(self):
        resolver, _ = self.resolver()
        claims = {**self.claims, "exp": 2_000_000_000, "scope": "ninai:read ninai:propose"}
        verifier = MCPTokenVerifier(FakeValidator(claims), resolver)
        access = asyncio.run(verifier.verify_token("signed.jwt"))
        self.assertIsNotNone(access)
        self.assertEqual(access.user_id, "user-1")
        self.assertEqual(access.workspace_id, "workspace-1")
        self.assertEqual(access.client_connection_id, "client-1")
        self.assertEqual(access.claims["workspace_id"], "workspace-1")
        self.assertEqual(access.scopes, ["ninai:read", "ninai:propose"])

    def test_mcp_verifier_returns_none_for_revoked_client(self):
        resolver, _ = self.resolver(None)
        verifier = MCPTokenVerifier(FakeValidator({**self.claims, "exp": 2_000_000_000}), resolver)
        self.assertIsNone(asyncio.run(verifier.verify_token("signed.jwt")))

    def test_oversized_bearer_is_rejected_before_validation_or_database_access(self):
        resolver, db = self.resolver()
        validator = FakeValidator({**self.claims, "exp": 2_000_000_000})
        verifier = MCPTokenVerifier(validator, resolver)
        self.assertIsNone(asyncio.run(verifier.verify_token("x" * 8193)))
        self.assertIsNone(validator.token)
        self.assertIsNone(db.params)

    def test_jwt_validator_checks_signature_issuer_audience_expiry_and_resource(self):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        validator = JWTValidator(self.settings)
        validator._keys = type("Keys", (), {"get_signing_key_from_jwt": lambda _self, _token:
                               type("Key", (), {"key": private_key.public_key()})()})()
        base = {
            **self.claims, "iss": self.settings.issuer, "aud": self.settings.audience,
            "resource": self.settings.resource, "exp": int(time.time()) + 60,
        }
        token = jwt.encode(base, private_key, algorithm="RS256", headers={"kid": "test"})
        self.assertEqual(validator.validate(token)["sub"], "user-1")

        wrong_resource = jwt.encode(
            {**base, "resource": "https://other.test/mcp"}, private_key, algorithm="RS256"
        )
        with self.assertRaisesRegex(AuthenticationError, "not valid for this resource"):
            validator.validate(wrong_resource)
        expired = jwt.encode({**base, "exp": int(time.time()) - 1}, private_key, algorithm="RS256")
        with self.assertRaisesRegex(AuthenticationError, "validation failed"):
            validator.validate(expired)

    def test_pat_mode_must_be_explicit_and_valid(self):
        self.assertEqual(auth_mode({}), "oauth")
        self.assertEqual(auth_mode({"NINAI_AUTH_MODE": "pat"}), "pat")
        with self.assertRaisesRegex(ValueError, "oauth.*pat"):
            auth_mode({"NINAI_AUTH_MODE": "basic"})

    def test_pat_verifier_hashes_token_and_returns_database_identity(self):
        raw = "ninai_pat_secret-that-is-never-stored"
        db = PATFakeDb({"user_id": "user-1", "workspace_id": "workspace-1",
                        "client_connection_id": "client-1", "expires_at": 2_000_000_000})
        @contextmanager
        def connect(): yield db
        access = asyncio.run(PATTokenVerifier(connect, "https://ninai.test/mcp").verify_token(raw))
        self.assertIsNotNone(access)
        self.assertEqual(access.client_id, "client-1")
        self.assertEqual(access.claims["auth_mode"], "pat")
        expected = hashlib.sha256(raw.encode()).hexdigest()
        self.assertEqual(db.calls[0][1], (expected,))
        self.assertEqual(db.calls[1][1], (expected,))
        self.assertNotIn(raw, " ".join(sql for sql, _ in db.calls))

    def test_pat_verifier_rejects_expired_or_revoked_token(self):
        db = PATFakeDb(None)
        @contextmanager
        def connect(): yield db
        self.assertIsNone(asyncio.run(PATTokenVerifier(connect, "https://ninai.test/mcp")
                                      .verify_token("expired")))
        self.assertEqual(len(db.calls), 1)

    def test_oversized_pat_is_rejected_without_hashing_or_database_access(self):
        db = PATFakeDb(None)
        @contextmanager
        def connect(): yield db
        self.assertIsNone(asyncio.run(PATTokenVerifier(connect, "https://ninai.test/mcp")
                                      .verify_token("x" * 513)))
        self.assertEqual(db.calls, [])


if __name__ == "__main__":
    unittest.main()
