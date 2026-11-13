#!/usr/bin/env python3
"""Opt-in Codex natural-prompt gate against synthetic localhost hosted memory.

Uses existing Codex login; model calls consume usage. No global config changes,
production credentials, local vault access, or implicit skill installation.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from verify_hosted_http import validate_targets, bounded_database_url, cleanup_fixture
from ninai_cloud.bootstrap import bootstrap
from ninai_cloud.postgres_store import PostgresStore, Principal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-url', required=True)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--with-continuity-skill', action='store_true',
                        help='Install the repository skill only in the isolated test workspace')
    args = parser.parse_args()
    validate_targets(args.database_url, args.endpoint)
    if not 10 <= args.timeout <= 180:
        parser.error('timeout must be 10..180 seconds')
    executable = shutil.which('codex')
    if not executable:
        parser.error('Codex CLI is required')
    database_url = bounded_database_url(args.database_url)
    evidence = Path(tempfile.mkdtemp(prefix='ninai-implicit-cloud-')).resolve()
    evidence.chmod(0o700)
    if args.with_continuity_skill:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine' / 'src'))
        from ninai.integration_skill import install_continuity_skill
        install_continuity_skill(target_root=evidence / '.agents' / 'skills')
    print(json.dumps({'evidence_dir': str(evidence), 'mode': 'cloud-only', 'continuity_skill': args.with_continuity_skill}), flush=True)
    fixture = None
    checks = {}
    try:
        fixture = bootstrap(database_url, email=f'{uuid.uuid4().hex}@test.invalid',
                            workspace_name='Synthetic implicit gate', project_name='Atlas')
        store = PostgresStore(database_url)
        principal = Principal(fixture['user'], fixture['workspace'], fixture['codex_client'])
        marker = uuid.uuid4().hex
        seed = store.create_memory(principal, content=f'Atlas savings-plan commitments are reviewed on Tuesdays. Reference {marker}.',
            memory_type='decision', scope_kind='project', scope_id=fixture['project'],
            project_id=fixture['project'], source_uri='synthetic://implicit-gate/seed',
            idempotency_key='seed', activate=True)
        environment = os.environ.copy()
        environment['NINAI_IMPLICIT_TEST_TOKEN'] = fixture['tokens']['codex']
        cases = [
            ('prior-work', 'What did we decide about Atlas savings-plan commitments?', 'read'),
            ('browse', 'Show me some memories.', 'read'),
            ('durable-outcome', 'For Atlas, we have decided to review savings-plan commitments every second Thursday instead of Tuesdays. Summarize our decision.', 'write'),
            ('fresh-continuation', 'When do we review Atlas savings-plan commitments now?', 'updated'),
            ('review-required', 'For Atlas, we have decided that Morgan owns the savings-plan review. Summarize the decision.', 'proposal'),
            ('general-knowledge', 'What is the capital of France?', 'none'),
        ]
        previous_writes = 0
        for name, prompt, expectation in cases:
            if expectation == 'proposal':
                with store._connection() as db:
                    db.execute('UPDATE client_scope_grants SET can_auto_activate=false WHERE client_connection_id=%s', (fixture['codex_client'],))
            with store._connection() as db:
                before_ids = {str(row['id']) for row in db.execute('SELECT id FROM memories WHERE workspace_id=%s', (fixture['workspace'],)).fetchall()}
            command = [executable, 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral',
                '--skip-git-repo-check', '--sandbox', 'read-only', '--disable', 'hooks', '--disable', 'apps',
                '-c', 'approval_policy="never"', '--json',
                '-c', 'mcp_servers.ninai_cloud.url=' + json.dumps(args.endpoint),
                '-c', 'mcp_servers.ninai_cloud.bearer_token_env_var="NINAI_IMPLICIT_TEST_TOKEN"',
                '-c', 'mcp_servers.ninai_cloud.default_tools_approval_mode="approve"',
                '-c', 'developer_instructions="This is an isolated test. You may read a selected installed skill, but do not inspect other files, run unrelated commands, or access unrelated services. Answer the user using permitted connected tools when appropriate."', prompt]
            # Fresh process per prompt. No brand, tool name, or instruction to save in the user prompt.
            with store._connection() as db:
                before = db.execute('SELECT count(*) AS n FROM disclosure_logs WHERE workspace_id=%s', (fixture['workspace'],)).fetchone()['n']
            result = subprocess.run(command, cwd=evidence, env=environment, capture_output=True, text=True, timeout=args.timeout)
            (evidence / f'{name}.jsonl').write_text(result.stdout.replace(environment['NINAI_IMPLICIT_TEST_TOKEN'], '[REDACTED]'))
            # Redact even synthetic bearer values if a host echoes its config.
            (evidence / f'{name}.stderr').write_text(result.stderr.replace(environment['NINAI_IMPLICIT_TEST_TOKEN'], '[REDACTED]'))
            with store._connection() as db:
                rows = db.execute('SELECT returned_memory_ids FROM disclosure_logs WHERE workspace_id=%s ORDER BY created_at', (fixture['workspace'],)).fetchall()
                writes = db.execute('SELECT id,content,status FROM memories WHERE workspace_id=%s AND id<>%s', (fixture['workspace'], seed.id)).fetchall()
            disclosed = any(seed.id in [str(value) for value in row['returned_memory_ids']] for row in rows[before:])
            events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            tool_calls = [event.get('item', {}) for event in events
                          if event.get('item', {}).get('type') == 'mcp_tool_call']
            answer = ' '.join(event.get('item', {}).get('text', '') for event in events
                              if event.get('item', {}).get('type') == 'agent_message').lower()
            if expectation == 'read':
                passed = disclosed
            elif expectation == 'write':
                passed = any('thursday' in row['content'].lower() and row['status'] == 'active' for row in writes)
            elif expectation == 'updated':
                updated_ids = {str(row['id']) for row in writes if 'thursday' in row['content'].lower()}
                passed = 'thursday' in answer and any(updated_ids.intersection(str(value) for value in row['returned_memory_ids']) for row in rows[before:])
            elif expectation == 'proposal':
                new = [row for row in writes if str(row['id']) not in before_ids]
                passed = (bool(new) and all(row['status'] == 'proposed' for row in new)
                          and any('morgan' in row['content'].lower() for row in new)
                          and any(call.get('tool') == 'propose_memory' for call in tool_calls)
                          and any(word in answer for word in ('review', 'pending', 'proposed')))
            else:
                passed = not tool_calls and len(rows) == before and len(writes) == previous_writes
            checks[name] = result.returncode == 0 and passed
            print(json.dumps({'case': name, 'passed': checks[name], 'host_exit': result.returncode}), flush=True)
            if result.returncode:
                break  # Quota/auth failures are blockers, not successful evaluations.
            previous_writes = len(writes)
        report = {'passed': len(checks) == len(cases) and all(checks.values()),
                  'checks': checks, 'evidence_dir': str(evidence)}
    finally:
        if fixture is not None:
            if not cleanup_fixture(database_url, fixture):
                raise RuntimeError('Synthetic fixture cleanup failed')
    report['cleanup_verified'] = True
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
