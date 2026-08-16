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
    OAuthControlTokenVerifier, OAuthIdentityResolver, PrincipalResolver,
    PATTokenVerifier, auth_mode,
)


class FakeResult:
    def __init__(self, row): self.row = row
    def fetchone(self): return self.row


class FakeDb:
    def __init__(self, row):
        self.row = row
        self.params = None
    def execute(self, _sql, params): self.params = params; return FakeResult(self.row)


class PATFakeDb:
    def __init__(self, row): self.row, self.calls = row, []
    def execute(self, sql, params):
        self.calls.append((sql, params))
        return FakeResult(self.row if sql.lstrip().startswith("SELECT") else None)


class SequenceDb:
    def __init__(self, rows): self.rows, self.calls = list(rows), []
    def execute(self, sql, params):
        self.calls.append((sql, params))
        row = self.rows.pop(0) if sql.lstrip().startswith("SELECT") else None
        return FakeResult(row)


class FakeValidator:
    def __init__(self, claims): self.claims, self.token = claims, None
    def validate(self, token): self.token = token; return self.claims


class FakeIdentities:
    def __init__(self, user_id="user-uuid", workspace_id="11111111-1111-4111-8111-111111111111"):
        self.user_id, self.workspace_id, self.created = user_id, workspace_id, None
    def resolve_user(self, claims, create=False):
        self.created = create
        return self.user_id
    def workspace_for(self, user_id, requested=None):
        return str(requested or self.workspace_id) if self.workspace_id else None


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.settings = AuthSettings(
            issuer="https://issuer.test", audience="ninai", resource="https://api.test/mcp",
            jwks_uri="https://issuer.test/jwks",
        )
        self.workspace_id = "11111111-1111-4111-8111-111111111111"
        self.claims = {"sub": "auth0|external-user", "client_id": "tpc_dynamic-client",
                       "https://ninai.io/workspace_id": self.workspace_id}

    def resolver(self, row="default"):
        if row == "default":
            row = {"user_id": "user-uuid", "workspace_id": self.workspace_id,
                   "client_connection_id": "client-1"}
        db = FakeDb(row)
        @contextmanager
        def connect(): yield db
        resolver = PrincipalResolver(connect, self.settings)
        resolver.identities = FakeIdentities()
        return resolver, db

    def test_metadata_points_to_external_issuer(self):
        metadata = self.settings.protected_resource_metadata()
        self.assertEqual(metadata["resource"], "https://api.test/mcp")
        self.assertEqual(metadata["authorization_servers"], ["https://issuer.test"])
        self.assertEqual(self.settings.authorization_server_metadata()["jwks_uri"], "https://issuer.test/jwks")

    def test_principal_comes_only_from_signed_claims_and_is_checked_live(self):
        resolver, db = self.resolver()
        principal = resolver.resolve(self.claims)
        self.assertEqual(principal.user_id, "user-uuid")
        self.assertEqual(principal.workspace_id, self.workspace_id)
        self.assertEqual(db.params, ("user-uuid", "https://issuer.test", "tpc_dynamic-client",
                                     "user-uuid", self.workspace_id, self.workspace_id))

    def test_revoked_client_is_rejected(self):
        resolver, _ = self.resolver(None)
        with self.assertRaisesRegex(AuthenticationError, "not connected.*revoked"):
            resolver.resolve(self.claims)

    def test_new_oauth_client_is_bound_without_silent_scope_grants(self):
        db = SequenceDb([
            None,
            None,
            {"workspace_id": self.workspace_id, "workspace_count": 1},
        ])
        @contextmanager
        def connect(): yield db
        resolver = PrincipalResolver(connect, self.settings)
        resolver.identities = FakeIdentities()
        principal = resolver.resolve({**self.claims, "client_name": "Claude"})
        self.assertEqual(principal.workspace_id, self.workspace_id)
        self.assertEqual(len([sql for sql, _ in db.calls if "INSERT INTO client_connections" in sql]), 1)
        self.assertEqual(len([sql for sql, _ in db.calls if "INSERT INTO oauth_client_bindings" in sql]), 1)
        self.assertFalse(any("client_scope_grants" in sql for sql, _ in db.calls))

    def test_revoked_oauth_binding_is_not_auto_recreated(self):
        db = SequenceDb([None, {"revoked_at": "2026-07-26"}])
        @contextmanager
        def connect(): yield db
        resolver = PrincipalResolver(connect, self.settings)
        resolver.identities = FakeIdentities()
        with self.assertRaisesRegex(AuthenticationError, "not connected.*revoked"):
            resolver.resolve(self.claims)
        self.assertFalse(any(sql.lstrip().startswith("INSERT") for sql, _ in db.calls))

    def test_missing_identity_claim_is_rejected(self):
        resolver, _ = self.resolver()
        with self.assertRaisesRegex(AuthenticationError, "OAuth client identity"):
            resolver.resolve({"sub": "auth0|external-user"})

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
        self.assertEqual(access.user_id, "user-uuid")
        self.assertEqual(access.workspace_id, self.workspace_id)
        self.assertEqual(access.client_connection_id, "client-1")
        self.assertEqual(access.claims["workspace_id"], self.workspace_id)
        self.assertEqual(access.scopes, ["ninai:read", "ninai:propose"])

    def test_mcp_verifier_accepts_audience_token_without_custom_scopes(self):
        """Authorization is enforced by live Ninai project grants, not host scope support."""
        resolver, _ = self.resolver()
        claims = {**self.claims, "exp": 2_000_000_000, "scope": "openid profile email"}
        verifier = MCPTokenVerifier(FakeValidator(claims), resolver)
        access = asyncio.run(verifier.verify_token("signed.jwt"))
        self.assertIsNotNone(access)
        self.assertEqual(access.client_connection_id, "client-1")
        self.assertEqual(access.scopes, ["openid", "profile", "email"])

    def test_mcp_verifier_returns_none_for_revoked_client(self):
        resolver, _ = self.resolver(None)
        verifier = MCPTokenVerifier(FakeValidator({**self.claims, "exp": 2_000_000_000}), resolver)
        self.assertIsNone(asyncio.run(verifier.verify_token("signed.jwt")))

    def test_control_oauth_verifier_allows_signed_first_workspace_identity(self):
        claims = {"sub": "auth0|external-user", "email": "owner@example.test", "name": "Owner",
                  "exp": 2_000_000_000}
        validator = FakeValidator(claims)
        identities = FakeIdentities()
        access = asyncio.run(OAuthControlTokenVerifier(validator, self.settings, identities)
                             .verify_token("signed.jwt"))
        self.assertEqual(access.claims, {"user_id": "user-uuid", "workspace_id": self.workspace_id,
                                         "email": "owner@example.test",
                                         "name": "Owner"})
        self.assertTrue(identities.created)
        self.assertEqual(validator.token, "signed.jwt")

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
        self.assertEqual(validator.validate(token)["sub"], "auth0|external-user")

        wrong_resource = jwt.encode(
            {**base, "resource": "https://other.test/mcp"}, private_key, algorithm="RS256"
        )
        with self.assertRaisesRegex(AuthenticationError, "not valid for this resource"):
            validator.validate(wrong_resource)
        expired = jwt.encode({**base, "exp": int(time.time()) - 1}, private_key, algorithm="RS256")
        with self.assertRaisesRegex(AuthenticationError, "validation failed"):
            validator.validate(expired)

    def test_auth0_audience_can_bind_resource_without_resource_claim(self):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa

        settings = AuthSettings(
            issuer="https://tenant.auth0.com/", audience="https://api.test/mcp",
            resource="https://api.test/mcp", jwks_uri="https://tenant.auth0.com/.well-known/jwks.json",
        )
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        validator = JWTValidator(settings)
        validator._keys = type("Keys", (), {"get_signing_key_from_jwt": lambda _self, _token:
                               type("Key", (), {"key": private_key.public_key()})()})()
        claims = {"iss": settings.issuer, "aud": settings.audience,
                  "sub": "auth0|abc", "client_id": "tpc_abc", "exp": int(time.time()) + 60}
        token = jwt.encode(claims, private_key, algorithm="RS256")
        self.assertEqual(validator.validate(token)["sub"], "auth0|abc")

    def test_external_subject_is_never_used_as_internal_user_id(self):
        calls = []
        class Db:
            def execute(self, sql, params):
                calls.append((sql, params))
                if "SELECT user_id FROM oauth_identities" in sql:
                    return FakeResult({"user_id": "08b59d77-7dd8-4c3f-b878-049b81ceac70"})
                return FakeResult(None)
        @contextmanager
        def connect(): yield Db()
        user_id = OAuthIdentityResolver(connect, self.settings).resolve_user(
            {"sub": "auth0|not-a-uuid"}
        )
        self.assertEqual(user_id, "08b59d77-7dd8-4c3f-b878-049b81ceac70")
        self.assertEqual(calls[0][1], (self.settings.issuer, "auth0|not-a-uuid"))

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
