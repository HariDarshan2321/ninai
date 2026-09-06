from __future__ import annotations

import unittest
import uuid
from contextlib import contextmanager
from unittest.mock import patch

from mcp.server.auth.provider import AccessToken, TokenVerifier
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from ninai_cloud.auth import AuthSettings
from ninai_cloud.control_api import ControlApp, ControlIdentity, ControlService
from ninai_cloud.postgres_store import AuthorizationError

ADMIN = str(uuid.UUID(int=1))
MEMBER = str(uuid.UUID(int=2))


class Database:
    def __init__(self):
        self.calls = []
        self.deleted = False
        self.login_count = 0

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        self.sql, self.params = sql, params
        if 'UPDATE users SET last_login_at' in sql and not self.deleted:
            self.login_count += 1
        return self

    def fetchone(self):
        if 'SELECT count(*) AS n' in self.sql:
            return {'n': 0}
        if 'AS signups_7d' in self.sql:
            return dict(users=0, signups_7d=0, signed_in_7d=0, downloaders=0,
                        downloads=0, workspaces=0, connections=0)
        return None if self.deleted else {'id': ADMIN}

    def fetchall(self):
        return []


class Verifier(TokenVerifier):
    async def verify_token(self, token):
        if token not in {'admin', 'member', 'agent'}:
            return None
        return AccessToken(token=token, client_id='agent-client' if token == 'agent' else 'dashboard',
                           scopes=[], subject='auth0|'+token, claims={'user_id': MEMBER if token == 'member' else ADMIN})


class AdminTest(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        @contextmanager
        def connect():
            yield self.db
        self.service = ControlService(connect, platform_admin_user_ids=frozenset({ADMIN}))
        self.settings = AuthSettings(issuer='https://issuer.example/', audience='https://ninai.example/mcp',
            resource='https://ninai.example/mcp', jwks_uri='https://issuer.example/jwks',
            authorization_endpoint='https://issuer.example/authorize', token_endpoint='https://issuer.example/token',
            control_client_id='dashboard', control_base_url='https://ninai.example')
        endpoint = ControlApp(self.service, Verifier(), self.settings).handle
        self.client = TestClient(Starlette(routes=[Route('/control', endpoint),
            Route('/control/admin', endpoint), Route('/api/control/{path:path}', endpoint, methods=['GET', 'POST'])]))

    def test_default_admin_access_is_disabled(self):
        with patch.dict('os.environ', {'NINAI_PLATFORM_ADMIN_USER_IDS': ''}):
            service = ControlService(self.service._connect)
        self.assertFalse(service.is_platform_admin(ControlIdentity(ADMIN, None)))
        self.assertEqual(self.db.calls, [])

    def test_all_admin_routes_reject_anonymous_members_and_agent_tokens(self):
        for path in ['/control/admin', '/api/control/admin/overview', '/api/control/admin/users',
                     '/api/control/admin/users/' + MEMBER]:
            for token, status in [('', 401), ('invalid', 401), ('member', 403), ('agent', 403)]:
                with self.subTest(path=path, token=token):
                    response = self.client.get(path, headers={'Authorization': 'Bearer '+token,
                        'X-User-Id': ADMIN, 'X-Role': 'admin'})
                    self.assertEqual(response.status_code, status)
                    self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.db.calls, [])

    def test_admin_access_checks_active_account_on_every_request(self):
        headers = {'Authorization': 'Bearer admin'}
        self.assertEqual(self.client.get('/control/admin', headers=headers).status_code, 200)
        self.db.deleted = True
        self.assertEqual(self.client.get('/control/admin', headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/api/control/admin/overview', headers=headers).status_code, 403)

    def test_overview_and_page_refresh_do_not_count_logins(self):
        for _ in range(2):
            self.assertEqual(self.client.get('/api/control/admin/overview',
                headers={'Authorization': 'Bearer admin'}).status_code, 200)
        self.assertEqual(self.db.login_count, 0)

    def test_search_is_bound_and_pagination_is_capped(self):
        response = self.client.get('/api/control/admin/users',
            params={'q': "%' OR true --", 'limit': 9999, 'offset': -8}, headers={'Authorization': 'Bearer admin'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['limit'], 100)
        self.assertEqual(response.json()['offset'], 0)
        sql, params = self.db.calls[-1]
        self.assertNotIn("OR true", sql)
        self.assertEqual(params, ("%' OR true --", "%' OR true --", 100, 0))
        for path in ['/api/control/admin/users?limit=abc', '/api/control/admin/users/not-a-uuid']:
            self.assertEqual(self.client.get(path, headers={'Authorization': 'Bearer admin'}).status_code, 400)

    def test_details_never_query_memory_bodies_or_credentials(self):
        response = self.client.get('/api/control/admin/users/'+MEMBER, headers={'Authorization': 'Bearer admin'})
        self.assertEqual(response.status_code, 200)
        for sql, _ in self.db.calls:
            for forbidden in ('memories', 'memory_sources', 'session_artifacts', 'personal_access_tokens', 'metadata_json'):
                self.assertNotIn(forbidden, sql)
        self.assertEqual(set(response.json()), {'user', 'workspaces', 'connections', 'downloads'})

    def test_callback_records_only_valid_dashboard_logins_and_redirects_admin(self):
        for access_token, expected, destination in [('admin', 302, '/control/admin'),
                ('member', 302, '/control'), ('invalid', 401, None), ('agent', 401, None)]:
            with self.subTest(token=access_token):
                before = self.db.login_count
                class TokenResponse:
                    def raise_for_status(self): pass
                    def json(self): return {'access_token': access_token, 'expires_in': 900}
                class Client:
                    def __init__(self, **kwargs): pass
                    async def __aenter__(self): return self
                    async def __aexit__(self, *args): pass
                    async def post(self, *args, **kwargs): return TokenResponse()
                    async def get(self, *args, **kwargs):
                        class Profile:
                            def raise_for_status(self): pass
                            def json(self): return {'sub': 'auth0|'+access_token, 'email': 'person@example.test', 'name': 'Person'}
                        return Profile()
                self.client.cookies.set('ninai_oauth_state', 'state')
                self.client.cookies.set('ninai_pkce_verifier', 'verifier')
                with patch('httpx.AsyncClient', Client):
                    response = self.client.get('/control?code=code&state=state', follow_redirects=False)
                self.assertEqual(response.status_code, expected)
                self.assertEqual(self.db.login_count-before, 1 if expected == 302 else 0)
                if destination:
                    self.assertEqual(response.headers['location'], destination)
                    login = next(params for sql, params in reversed(self.db.calls) if 'UPDATE users SET last_login_at' in sql)
                    self.assertEqual(login[:2], ('person@example.test', 'Person'))
                else:
                    self.assertNotIn('__Host-ninai_access_token=', response.headers.get('set-cookie', ''))

    def test_deleted_account_cannot_complete_login(self):
        self.db.deleted = True
        with self.assertRaises(AuthorizationError):
            self.service.record_login(ControlIdentity(ADMIN, None))
        self.assertEqual(self.db.login_count, 0)

    def test_profile_subject_mismatch_cannot_create_session(self):
        class TokenResponse:
            def raise_for_status(self): pass
            def json(self): return {'access_token': 'admin', 'expires_in': 900}
        class ProfileResponse:
            def raise_for_status(self): pass
            def json(self): return {'sub': 'auth0|someone-else', 'email': 'wrong@example.test'}
        class Client:
            def __init__(self, **kwargs): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def post(self, *args, **kwargs): return TokenResponse()
            async def get(self, *args, **kwargs): return ProfileResponse()
        self.client.cookies.set('ninai_oauth_state', 'state')
        self.client.cookies.set('ninai_pkce_verifier', 'verifier')
        with patch('httpx.AsyncClient', Client):
            response = self.client.get('/control?code=code&state=state', follow_redirects=False)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db.login_count, 0)
        self.assertNotIn('__Host-ninai_access_token=', response.headers.get('set-cookie', ''))


if __name__ == '__main__':
    unittest.main()
