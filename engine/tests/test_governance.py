from __future__ import annotations
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ninai.governance import OwnerVerificationAuthority
from ninai.store import MemoryStore

class AccessRequestsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = MemoryStore(Path(self.temp.name) / 'vault.sqlite3')
        self.project = self.store.ensure_project(name='Work', binding_key='work', cwd_or_repo='/work')
        self.authority = OwnerVerificationAuthority(lambda snapshot: True)

    def request(self, **overrides):
        values = dict(client_id='codex', project_id=self.project['id'], actions=['read', 'write'],
                      reason='Continue work on this project', idempotency_key='proposal-1')
        values.update(overrides)
        return self.store.create_access_request(**values)

    def approve(self, request):
        ticket = self.authority.verify(request)
        return self.store.approve_access_request(request['id'], ticket=ticket, authority=self.authority)

    def test_no_grants_before_review_and_exact_approved_set(self):
        request = self.request()
        self.assertEqual(self.store.project_permissions('codex'), [])
        self.assertEqual(self.approve(request)['status'], 'approved')
        self.assertEqual({p['action'] for p in self.store.project_permissions('codex') if p['allowed']}, {'read', 'write'})
        self.assertFalse(self.store.can_access_project('other', self.project['id']))

    def test_delete_only_has_no_implicit_read_write(self):
        self.approve(self.request(actions=['delete']))
        self.assertEqual([p['action'] for p in self.store.project_permissions('codex') if p['allowed']], ['delete'])

    def test_requests_private_and_idempotent(self):
        request = self.request()
        self.assertEqual(request, self.request(actions=['write', 'read']))
        with self.assertRaises(ValueError):
            self.store.get_access_request(request['id'], client_id='other')
        with self.assertRaises(ValueError):
            self.request(actions=['delete'])

    def test_fake_verification_rejected(self):
        request = self.request()
        with self.assertRaises(PermissionError):
            self.store.approve_access_request(request['id'], ticket='guessed', authority=self.authority)
        with self.assertRaises(PermissionError):
            self.store.approve_access_request(request['id'], ticket='guessed', authority=True)
        for result in [False, None, 'true', 1]:
            with self.assertRaises(PermissionError):
                OwnerVerificationAuthority(lambda _: result).verify(request)
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_ticket_one_use_and_exact_request(self):
        first = self.request()
        second = self.request(idempotency_key='proposal-2', actions=['delete'])
        ticket = self.authority.verify(first)
        with self.assertRaises(PermissionError):
            self.store.approve_access_request(second['id'], ticket=ticket, authority=self.authority)
        with self.assertRaises(PermissionError):
            self.store.approve_access_request(first['id'], ticket=ticket, authority=self.authority)
        ticket = self.authority.verify(first)
        self.store.approve_access_request(first['id'], ticket=ticket, authority=self.authority)
        with self.assertRaises(PermissionError):
            self.store.approve_access_request(first['id'], ticket=ticket, authority=self.authority)

    def test_ticket_expiry(self):
        request = self.request()
        with patch('ninai.governance.time.monotonic', return_value=100):
            ticket = self.authority.verify(request)
        with patch('ninai.governance.time.monotonic', return_value=161):
            with self.assertRaises(PermissionError):
                self.store.approve_access_request(request['id'], ticket=ticket, authority=self.authority)
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_request_expiry(self):
        request = self.request(expires_in_seconds=60)
        ticket = self.authority.verify(request)
        with patch('ninai.store.time.time', return_value=request['expires_at'] + 1):
            with self.assertRaises((PermissionError, ValueError)):
                self.store.approve_access_request(request['id'], ticket=ticket, authority=self.authority)
            self.assertEqual(self.store.get_access_request(request['id'])['status'], 'expired')
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_permission_revision_catches_aba(self):
        request = self.request()
        ticket = self.authority.verify(request)
        self.store.grant_project('codex', self.project['id'], 'delete')
        self.store.revoke_project('codex', self.project['id'], 'delete')
        self.assertEqual(self.store.get_access_request(request['id'])['status'], 'stale')
        with self.assertRaises((ValueError, PermissionError)):
            self.store.approve_access_request(request['id'], ticket=ticket, authority=self.authority)
        self.assertFalse(self.store.can_access_project('codex', self.project['id'], 'read'))

    def test_deleted_project_invalidates_review(self):
        request = self.request()
        ticket = self.authority.verify(request)
        with self.store._connection() as db:
            db.execute('DELETE FROM projects WHERE id=?', (self.project['id'],))
        with self.assertRaises((ValueError, PermissionError)):
            self.store.approve_access_request(request['id'], ticket=ticket, authority=self.authority)
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_denial_restart_and_verifier_failure_do_not_authorize(self):
        request = self.request()
        ticket = self.authority.verify(request)
        self.assertEqual(self.store.deny_access_request(request['id'])['status'], 'denied')
        with self.assertRaises((ValueError, PermissionError)):
            self.store.approve_access_request(request['id'], ticket=ticket, authority=self.authority)
        with self.assertRaises(PermissionError):
            self.store.approve_access_request(request['id'], ticket=ticket, authority=OwnerVerificationAuthority(lambda _: True))
        def cancelled(_):
            raise RuntimeError('cancelled')
        with self.assertRaises(RuntimeError):
            OwnerVerificationAuthority(cancelled).verify(self.request(idempotency_key='second'))
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_bounded_validation(self):
        for overrides in [dict(actions=[]), dict(actions=[{}]), dict(actions=['*']), dict(actions=['read', 'read']),
                          dict(actions=['read', 'admin']), dict(reason=''), dict(reason='x' * 1001),
                          dict(expires_in_seconds=0), dict(expires_in_seconds=True),
                          dict(expires_in_seconds=604801), dict(project_id='unknown'),
                          dict(idempotency_key='x' * 129)]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.request(**overrides)

    def test_mcp_binds_client_and_exposes_no_approval(self):
        from ninai import server
        self.assertNotIn('client_id', inspect.signature(server.request_project_access).parameters)
        with patch.object(server, 'get_store', return_value=self.store), patch.object(server, 'configured_client_id', return_value='codex'):
            request = json.loads(server.request_project_access(self.project['id'], ['read'], 'Review context', 'mcp-1'))['request']
            self.assertEqual(request['client_id'], 'codex')
            self.assertEqual(json.loads(server.access_request_status(request['id']))['request']['id'], request['id'])
        with patch.object(server, 'get_store', return_value=self.store), patch.object(server, 'configured_client_id', return_value='other'):
            self.assertIn('error', json.loads(server.access_request_status(request['id'])))
        self.assertFalse(hasattr(server, 'approve_access_request'))
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_direct_owner_snapshots_exact_grants_and_one_use(self):
        targets = [dict(project_id=self.project['id']), dict(scope='personal'), dict(scope='project')]
        for action, target in zip(['write', 'read', 'delete'], targets):
            snapshot = self.store.owner_permission_snapshot('codex', action, **target)
            self.assertFalse(snapshot['current_allowed'])
            ticket = self.authority.verify(snapshot)
            result = self.store.apply_owner_permission_change(snapshot, ticket=ticket, authority=self.authority)
            self.assertTrue(result['allowed'])
            self.assertTrue(self.store.owner_permission_snapshot('codex', action, **target)['current_allowed'])
            with self.assertRaises(PermissionError):
                self.store.apply_owner_permission_change(snapshot, ticket=ticket, authority=self.authority)
        self.assertFalse(self.store.can_access_project('codex', self.project['id'], 'read'))
        caps = {p['scope']: p for p in self.store.permissions('codex')}
        self.assertFalse(caps['project']['allowed'])
        self.assertTrue(caps['project']['can_delete'])
        self.assertFalse(caps['personal']['can_write'])

    def test_direct_owner_revoke_during_verification_is_preserved(self):
        # Exercise project, legacy read, and scope capability revisions including ABA.
        targets = [(dict(project_id=self.project['id']), 'read',
                    lambda: self.store.grant_project('codex', self.project['id']),
                    lambda: self.store.revoke_project('codex', self.project['id'])),
                   (dict(scope='personal'), 'read',
                    lambda: self.store.grant('codex', 'personal'),
                    lambda: self.store.revoke('codex', 'personal')),
                   (dict(scope='project'), 'delete',
                    lambda: self.store.grant_action('codex', 'project', 'delete'),
                    lambda: self.store.revoke_action('codex', 'project', 'delete'))]
        for target, action, grant, revoke in targets:
            with self.subTest(target=target):
                snapshot = self.store.owner_permission_snapshot('codex', action, **target)
                ticket = self.authority.verify(snapshot)
                grant()
                revoke()
                with self.assertRaises(ValueError):
                    self.store.apply_owner_permission_change(snapshot, ticket=ticket, authority=self.authority)
                self.assertFalse(self.store.owner_permission_snapshot('codex', action, **target)['current_allowed'])
                with self.assertRaises(PermissionError):
                    self.store.apply_owner_permission_change(snapshot, ticket=ticket, authority=self.authority)

    def test_direct_owner_already_allowed_is_no_write(self):
        self.store.grant_project('codex', self.project['id'])
        snapshot = self.store.owner_permission_snapshot('codex', 'read', project_id=self.project['id'])
        before = self.store.project_permissions('codex')
        ticket = self.authority.verify(snapshot)
        self.store.apply_owner_permission_change(snapshot, ticket=ticket, authority=self.authority)
        after = self.store.owner_permission_snapshot('codex', 'read', project_id=self.project['id'])
        self.assertEqual(after['revision'], snapshot['revision'])
        self.assertEqual(before, self.store.project_permissions('codex'))

    def test_direct_owner_snapshot_tamper_and_deleted_project_rejected(self):
        snapshot = self.store.owner_permission_snapshot('codex', 'read', project_id=self.project['id'])
        ticket = self.authority.verify(snapshot)
        with self.assertRaises(PermissionError):
            self.store.apply_owner_permission_change({**snapshot, 'actions': ['delete']}, ticket=ticket, authority=self.authority)
        ticket = self.authority.verify(snapshot)
        with self.store._connection() as db:
            db.execute('DELETE FROM projects WHERE id=?', (self.project['id'],))
        with self.assertRaises(ValueError):
            self.store.apply_owner_permission_change(snapshot, ticket=ticket, authority=self.authority)
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_project_heartbeat_keeps_pending_review_and_ticket_valid(self):
        request = self.request()
        ticket = self.authority.verify(request)
        for _ in range(3):
            self.store.ensure_project(name='Work', binding_key='work', cwd_or_repo='/work')
        self.assertEqual(self.store.get_access_request(request['id']), request)
        self.assertEqual(self.store.approve_access_request(request['id'], ticket=ticket, authority=self.authority)['status'], 'approved')

    def test_timestamp_only_and_noop_policy_writes_keep_review_valid(self):
        self.store.grant_project('other', self.project['id'])
        self.store.grant('other', 'personal')
        self.store.grant_action('other', 'project', 'write')
        request = self.request()
        self.store.grant_project('other', self.project['id'])
        self.store.grant('other', 'personal')
        self.store.grant_action('other', 'project', 'write')
        with self.store._connection() as db:
            for table in ['projects', 'project_permissions', 'permissions', 'scope_capabilities']:
                db.execute(f"UPDATE {table} SET updated_at='heartbeat-fixture'")
        self.assertEqual(self.store.get_access_request(request['id'])['status'], 'pending')

    def test_project_rename_and_rename_aba_invalidate_review(self):
        request = self.request()
        ticket = self.authority.verify(request)
        with self.store._connection() as db:
            db.execute("UPDATE projects SET name='Renamed' WHERE id=?", (self.project['id'],))
        self.assertEqual(self.store.get_access_request(request['id'])['status'], 'stale')
        with self.store._connection() as db:
            db.execute("UPDATE projects SET name='Work' WHERE id=?", (self.project['id'],))
        with self.assertRaises((ValueError, PermissionError)):
            self.store.approve_access_request(request['id'], ticket=ticket, authority=self.authority)
        self.assertEqual(self.store.project_permissions('codex'), [])

    def test_existing_unconditional_triggers_upgrade_without_staling_review(self):
        request = self.request()
        with self.store._connection() as db:
            db.execute('DROP TRIGGER governance_projects_update')
            db.execute('''CREATE TRIGGER governance_projects_update AFTER UPDATE ON projects BEGIN
                UPDATE governance_revision SET revision=revision+1 WHERE id=1; END''')
        upgraded = MemoryStore(self.store.path)
        upgraded.ensure_project(name='Work', binding_key='work', cwd_or_repo='/work')
        self.assertEqual(upgraded.get_access_request(request['id'])['status'], 'pending')
        with upgraded._connection() as db:
            db.execute("UPDATE projects SET name='New name' WHERE id=?", (self.project['id'],))
        self.assertEqual(upgraded.get_access_request(request['id'])['status'], 'stale')

    def test_capture_directory_name_and_worktree_do_not_rename_or_stale_review(self):
        request = self.request()
        ticket = self.authority.verify(request)
        captured = self.store.ensure_project(name='work-repo-worktree', binding_key='work',
                                             cwd_or_repo='/another/worktree')
        self.assertEqual(captured['id'], self.project['id'])
        self.assertEqual(captured['name'], 'Work')
        self.assertEqual(captured['cwd_or_repo'], '/another/worktree')
        from ninai.session_capture import handle_lifecycle_event
        self.store.set_capture_enabled(True)
        with patch('ninai.session_capture._project_identity',
                   return_value=('work-repo-worktree', 'work', '/another/worktree')):
            handle_lifecycle_event({'hook_event_name': 'SessionStart', 'session_id': 'background-session',
                                    'cwd': '/another/worktree'}, provider='codex', store=self.store)
        self.assertEqual(self.store.list_projects()[0]['name'], 'Work')
        self.assertEqual(self.store.get_access_request(request['id']), request)
        self.assertEqual(self.store.approve_access_request(request['id'], ticket=ticket,
                                                          authority=self.authority)['status'], 'approved')
