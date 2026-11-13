"""Owner bridge verification tests, using isolated vaults and no OS prompts."""
from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from ninai.desktop.api import DesktopApi
from ninai.owner_verification import OwnerVerificationError
from ninai.store import MemoryStore


class DesktopGovernanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = MemoryStore(Path(self.temp.name) / 'vault.sqlite3')
        self.project = self.store.ensure_project(name='Alpha', binding_key='alpha', cwd_or_repo='/alpha')
        self.other = self.store.ensure_project(name='Beta', binding_key='beta', cwd_or_repo='/beta')

    def request(self, **overrides):
        values = dict(client_id='codex', project_id=self.project['id'], actions=['read', 'write'],
                      reason='Continue the requested implementation', idempotency_key='bridge-1')
        values.update(overrides)
        return self.store.create_access_request(**values)

    def test_native_cancel_or_failure_preserves_permissions_and_pending_request(self):
        self.store.grant_project('codex', self.project['id'], 'read')
        request = self.request(actions=['delete'])
        api = DesktopApi(self.store)
        before = self.store.project_permissions('codex')
        for reason in ['OS owner verification was cancelled', 'OS owner verification failed']:
            with self.subTest(reason=reason), patch('ninai.desktop.api.verify_owner', side_effect=OwnerVerificationError(reason)) as verify:
                result = api.approve_access_request(request['id'])
                self.assertFalse(result['ok'])
                self.assertIn(reason, result['error'])
                verify.assert_called_once()
                prompt = verify.call_args.args[0]
                self.assertIn('codex', prompt)
                self.assertIn('delete', prompt)
                self.assertIn('Alpha', prompt)
                self.assertEqual(self.store.project_permissions('codex'), before)
                self.assertEqual(self.store.get_access_request(request['id'])['status'], 'pending')

    def test_trusted_callback_approves_exact_request_and_cannot_replay(self):
        request = self.request(actions=['write', 'delete'])
        verifier = Mock(return_value=True)
        api = DesktopApi(self.store, owner_verifier=verifier)
        result = api.approve_access_request(request['id'])
        self.assertTrue(result['ok'])
        verifier.assert_called_once_with(request)
        self.assertEqual({item['action'] for item in self.store.project_permissions('codex') if item['allowed']}, {'write', 'delete'})
        self.assertFalse(self.store.can_access_project('codex', self.other['id']))
        self.assertFalse(self.store.can_access_project('other-client', self.project['id']))
        self.assertFalse(api.approve_access_request(request['id'])['ok'])
        verifier.assert_called_once()

    def test_js_has_no_verification_assertion_or_ticket_parameter(self):
        api = DesktopApi(self.store, owner_verifier=lambda _: True)
        request = self.request()
        self.assertEqual(list(inspect.signature(api.approve_access_request).parameters), ['request_id'])
        with self.assertRaises(TypeError):
            api.approve_access_request(request['id'], True)
        with self.assertRaises(TypeError):
            api.approve_access_request(request['id'], verified=True)
        self.assertEqual(self.store.project_permissions('codex'), [])
        from ninai import server
        tools = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
        self.assertIn('request_project_access', tools)
        self.assertIn('access_request_status', tools)
        self.assertFalse(any('approve' in name or 'verify' in name or 'grant' in name or 'deny' in name for name in tools))

    def test_list_shows_exact_current_permissions_without_prompt(self):
        self.store.grant_project('codex', self.project['id'], 'read')
        self.store.grant_project('codex', self.other['id'], 'delete')
        request = self.request()
        api = DesktopApi(self.store)
        with patch('ninai.desktop.api.verify_owner') as verify, patch('ninai.desktop.api.check_owner_verification', return_value={'available': True, 'method': 'fixture', 'reason': ''}):
            result = api.list_access_requests()
        self.assertTrue(result['ok'])
        self.assertEqual(result['data']['requests'][0]['id'], request['id'])
        self.assertEqual(result['data']['requests'][0]['current_permissions'], {'read': True, 'write': False, 'delete': False})
        verify.assert_not_called()

    def test_denial_needs_no_prompt_and_changes_no_access(self):
        request = self.request()
        api = DesktopApi(self.store)
        with patch('ninai.desktop.api.verify_owner') as verify:
            result = api.deny_access_request(request['id'])
        self.assertTrue(result['ok'])
        self.assertEqual(result['data']['status'], 'denied')
        verify.assert_not_called()
        self.assertEqual(self.store.project_permissions('codex'), [])
        self.assertFalse(api.approve_access_request(request['id'])['ok'])

    def test_false_and_non_boolean_trusted_results_do_not_grant(self):
        request = self.request()
        for verification in [False, None, 1, 'true']:
            with self.subTest(verification=verification):
                api = DesktopApi(self.store, owner_verifier=lambda _: verification)
                self.assertFalse(api.approve_access_request(request['id'])['ok'])
                self.assertEqual(self.store.project_permissions('codex'), [])

    def test_all_direct_grant_paths_fail_closed_and_revoke_immediately(self):
        api = DesktopApi(self.store)
        calls = [
            lambda allowed: api.set_project_permission('codex', self.project['id'], 'write', allowed),
            lambda allowed: api.set_capability('codex', 'project', 'delete', allowed),
            lambda allowed: api.set_permission('codex', 'personal', allowed),
        ]
        for index, operation in enumerate(calls):
            for message in ['cancelled', 'failed']:
                with self.subTest(path=index, outcome=message), patch('ninai.desktop.api.verify_owner', side_effect=OwnerVerificationError(message)) as verify:
                    self.assertFalse(operation(True)['ok'])
                    verify.assert_called_once()
                    self.assertFalse(self.store.can_access_project('codex', self.project['id'], 'write'))
                    self.assertNotIn('personal', self.store.allowed_scopes('codex'))
                    self.assertFalse(api.get_capabilities('codex')['data']['project']['delete'])
            with patch('ninai.desktop.api.verify_owner', return_value=object()) as verify:
                self.assertTrue(operation(True)['ok'])
                verify.assert_called_once()
            with patch('ninai.desktop.api.verify_owner', side_effect=AssertionError('Revocation must not prompt')) as verify:
                self.assertTrue(operation(False)['ok'])
                verify.assert_not_called()
        self.assertFalse(self.store.can_access_project('codex', self.project['id'], 'write'))
        self.assertNotIn('personal', self.store.allowed_scopes('codex'))
        self.assertFalse(api.get_capabilities('codex')['data']['project']['delete'])

    def test_permission_change_during_owner_modal_invalidates_request(self):
        request = self.request()
        def changed_while_prompting(_):
            self.store.grant_project('other-client', self.project['id'], 'delete')
            return True
        api = DesktopApi(self.store, owner_verifier=changed_while_prompting)
        result = api.approve_access_request(request['id'])
        self.assertFalse(result['ok'])
        self.assertEqual(self.store.get_access_request(request['id'])['status'], 'stale')
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_direct_grants_reject_revoke_during_owner_verification(self):
        cases = [
            (lambda api: api.set_project_permission('codex', self.project['id'], 'write', True),
             lambda: self.store.grant_project('codex', self.project['id'], 'write'),
             lambda: self.store.revoke_project('codex', self.project['id'], 'write'),
             dict(project_id=self.project['id']), 'write'),
            (lambda api: api.set_capability('codex', 'project', 'delete', True),
             lambda: self.store.grant_action('codex', 'project', 'delete'),
             lambda: self.store.revoke_action('codex', 'project', 'delete'), dict(scope='project'), 'delete'),
            (lambda api: api.set_permission('codex', 'personal', True),
             lambda: self.store.grant('codex', 'personal'),
             lambda: self.store.revoke('codex', 'personal'), dict(scope='personal'), 'read'),
        ]
        for index, (operation, grant, revoke, target, action) in enumerate(cases):
            with self.subTest(path=index):
                def concurrently_revoked(_):
                    grant()
                    revoke()
                    return True
                api = DesktopApi(self.store, owner_verifier=concurrently_revoked)
                self.assertFalse(operation(api)['ok'])
                self.assertFalse(self.store.owner_permission_snapshot('codex', action, **target)['current_allowed'])

    def test_redundant_direct_grants_neither_prompt_nor_regrant(self):
        cases = [
            (lambda api: api.set_project_permission('codex', self.project['id'], 'read', True),
             lambda: self.store.grant_project('codex', self.project['id']),
             dict(project_id=self.project['id']), 'read'),
            (lambda api: api.set_capability('codex', 'project', 'delete', True),
             lambda: self.store.grant_action('codex', 'project', 'delete'), dict(scope='project'), 'delete'),
            (lambda api: api.set_permission('codex', 'personal', True),
             lambda: self.store.grant('codex', 'personal'), dict(scope='personal'), 'read'),
        ]
        for index, (operation, grant, target, action) in enumerate(cases):
            with self.subTest(path=index):
                grant()
                before = self.store.owner_permission_snapshot('codex', action, **target)
                verifier = Mock(side_effect=AssertionError('No change must not prompt'))
                self.assertTrue(operation(DesktopApi(self.store, owner_verifier=verifier))['ok'])
                after = self.store.owner_permission_snapshot('codex', action, **target)
                self.assertEqual(before['revision'], after['revision'])
                verifier.assert_not_called()
