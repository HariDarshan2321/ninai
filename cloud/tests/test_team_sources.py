from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from ninai_cloud.team_sources import (
    SourceAccess,
    SourceProof,
    SourceRequest,
    SourceStatus,
    UnavailableSourceVerifier,
    parse_source_reference,
    proof_status,
    source_fingerprint,
    verified_fingerprint,
)


class SourceReferenceTests(unittest.TestCase):
    def test_github_pr_reference_normalizes_case_and_drops_query_and_anchor(self):
        reference = parse_source_reference(" https://GitHub.com/Example/Payments/pull/12/?tab=files#review ")
        self.assertEqual(reference.provider, "github")
        self.assertEqual(reference.resource_key, "example/payments/pull/12")
        self.assertEqual(reference.canonical_url, "https://github.com/example/payments/pull/12")
        self.assertEqual(parse_source_reference(reference.canonical_url), reference)

    def test_linear_issue_reference_drops_title(self):
        reference = parse_source_reference("https://linear.app/Team/issue/pay-23/retry-r%C3%A9sum%C3%A9")
        self.assertEqual(reference.provider, "linear")
        self.assertEqual(reference.resource_key, "team/issue/PAY-23")
        self.assertEqual(reference.canonical_url, "https://linear.app/team/issue/PAY-23")
        self.assertEqual(parse_source_reference(reference.canonical_url), reference)

    def test_notion_page_reference_is_stable_across_link_forms(self):
        page_id = "aabbccddee00112233445566778899aa"
        links = (
            f"https://www.notion.so/{page_id}?source=copy_link",
            f"https://www.notion.so/team/Design-note-{page_id}#heading",
            "https://team.notion.site/Design-note-AABBCCDD-EE00-1122-3344-5566778899AA",
        )
        references = [parse_source_reference(link) for link in links]
        self.assertTrue(all(reference == references[0] for reference in references))
        self.assertEqual(references[0].provider, "notion")
        self.assertEqual(references[0].resource_key, page_id)
        self.assertEqual(references[0].canonical_url, f"https://www.notion.so/{page_id}")

    def test_only_supported_https_hosts_and_resource_paths_are_accepted(self):
        invalid = (
            "http://github.com/Example/Payments/pull/12",
            "https://example.invalid/Example/Payments/pull/12",
            "https://github.com.example.invalid/Example/Payments/pull/12",
            "https://user@github.com/Example/Payments/pull/12",
            "https://github.com:443/Example/Payments/pull/12",
            "https://github.com/Example/Payments/issues/12",
            "https://github.com/Example//pull/12",
            "https://github.com/Example/Payments/pull/12/files",
            "https://github.com/Example/Payments/pull/12\n",
            "https://linear.app/acme/issue/PAY-23/invalid%XX",
            "https://linear.app/acme/team/PAY-23",
            "https://www.notion.so/Page-with-no-ID",
            "https://notion.so/?page=aabbccddee00112233445566778899aa",
        )
        for link in invalid:
            with self.subTest(link=link), self.assertRaisesRegex(ValueError, "Enter an HTTPS"):
                parse_source_reference(link)

    def test_fingerprint_binds_stable_resource_id_and_revision(self):
        fingerprint = source_fingerprint("github", "PR_node_001", "revision-1")
        self.assertRegex(fingerprint, "^[0-9a-f]{64}$")
        self.assertEqual(fingerprint, source_fingerprint("github", "PR_node_001", "revision-1"))
        for provider, resource, revision in (
            ("linear", "PR_node_001", "revision-1"),
            ("github", "PR_node_002", "revision-1"),
            ("github", "PR_node_001", "revision-2"),
        ):
            self.assertNotEqual(fingerprint, source_fingerprint(provider, resource, revision))


class SourceProofTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 21, tzinfo=timezone.utc)
        self.fingerprint = source_fingerprint("github", "PR_node_001", "revision-1")
        self.request = SourceRequest(
            workspace_id="workspace-a",
            project_id="project-a",
            user_id="member-a",
            binding_id="assistant-a",
            authorization_epoch=4,
            reference=parse_source_reference("https://github.com/example/payments/pull/12"),
            expected_fingerprint=self.fingerprint,
            request_id="request-1",
        )
        self.proof = SourceProof(self.request, self.now, SourceAccess.GRANTED, self.fingerprint)

    def test_matching_fresh_proof_verifies_current_evidence(self):
        self.assertEqual(proof_status(self.request, self.proof, now=self.now), SourceStatus.VERIFIED)
        self.assertIsNone(verified_fingerprint(self.request, self.proof, now=self.now))

    def test_proof_binds_requester_scope_generation_resource_and_request(self):
        mismatches = {
            "workspace_id": "workspace-b",
            "project_id": "project-b",
            "user_id": "member-b",
            "binding_id": None,
            "authorization_epoch": 5,
            "reference": parse_source_reference("https://github.com/example/payments/pull/13"),
            "expected_fingerprint": "0" * 64,
            "request_id": "request-2",
        }
        for field, value in mismatches.items():
            with self.subTest(field=field):
                request = replace(self.request, **{field: value})
                self.assertEqual(proof_status(request, self.proof, now=self.now), SourceStatus.UNKNOWN)

    def test_proof_cannot_be_reused_after_provider_age_limit(self):
        finalization = self.now + timedelta(seconds=5, microseconds=1)
        self.assertEqual(proof_status(self.request, self.proof, now=finalization), SourceStatus.UNKNOWN)

    def test_future_naive_and_noncanonical_proofs_are_unusable(self):
        proofs = (
            replace(self.proof, checked_at=self.now + timedelta(seconds=1)),
            replace(self.proof, checked_at=self.now.replace(tzinfo=None)),
        )
        for proof in proofs:
            self.assertEqual(proof_status(self.request, proof, now=self.now), SourceStatus.UNKNOWN)
        tampered = replace(self.request, reference=replace(self.request.reference, resource_key="wrong"))
        proof = replace(self.proof, request=tampered)
        self.assertEqual(proof_status(tampered, proof, now=self.now), SourceStatus.UNKNOWN)

    def test_affirmative_access_is_required_to_classify_evidence(self):
        variations = (
            (SourceAccess.GRANTED, "0" * 64, SourceStatus.CHANGED),
            (SourceAccess.GRANTED, None, SourceStatus.UNAVAILABLE),
            (SourceAccess.GRANTED, "invalid", SourceStatus.UNAVAILABLE),
            (SourceAccess.DENIED, self.fingerprint, SourceStatus.PERMISSION_DENIED),
            (SourceAccess.UNKNOWN, self.fingerprint, SourceStatus.UNKNOWN),
        )
        for access, fingerprint, status in variations:
            with self.subTest(access=access, status=status):
                proof = SourceProof(self.request, self.now, access, fingerprint)
                self.assertEqual(proof_status(self.request, proof, now=self.now), status)

    def test_review_can_pin_only_fresh_verified_evidence_for_unpinned_source(self):
        request = replace(self.request, expected_fingerprint=None)
        proof = replace(self.proof, request=request)
        self.assertEqual(verified_fingerprint(request, proof, now=self.now), self.fingerprint)
        self.assertEqual(proof_status(request, proof, now=self.now), SourceStatus.UNAVAILABLE)
        denied = replace(proof, access=SourceAccess.DENIED)
        self.assertIsNone(verified_fingerprint(request, denied, now=self.now))
        self.assertIsNone(verified_fingerprint(request, self.proof, now=self.now))

    def test_default_verifier_never_asserts_source_access(self):
        proof = UnavailableSourceVerifier().verify(self.request)
        self.assertEqual(proof_status(self.request, proof, now=self.now), SourceStatus.UNKNOWN)
        self.assertNotIn(self.request.reference.canonical_url, repr(self.request))
        self.assertNotIn(self.fingerprint, repr(self.proof))
