from __future__ import annotations

import io
import json
from http.client import IncompleteRead
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from ninai import updates


class UpdateCheckTest(unittest.TestCase):
    def check(self, release):
        with patch.object(updates, 'build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(json.dumps(release).encode())
            result = updates.check_for_updates()
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, updates.RELEASE_API)
            self.assertIsNone(request.data)
            self.assertNotIn('Authorization', dict(request.header_items()))
            self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], 5)
            return result

    def release(self, version='v99.0.0'):
        return {'tag_name': version, 'draft': False, 'prerelease': False,
                'published_at': '2026-11-12T12:00:00Z',
                'html_url': updates.RELEASE_PREFIX + version}

    def test_explicit_metadata_check_detects_update_without_installing(self):
        result = self.check(self.release())
        self.assertEqual(result['status'], 'update_available')
        self.assertEqual(result['latest_version'], '99.0.0')
        self.assertNotIn('download_url', result)

    def test_equal_older_and_newer_versions_are_distinct(self):
        self.assertEqual(self.check(self.release('v' + updates.__version__))['status'], 'current')
        self.assertEqual(self.check(self.release('v0.0.0'))['status'], 'ahead')

    def test_untrusted_or_unpublished_metadata_never_reports_current(self):
        for changes in ({'draft': True}, {'prerelease': True}, {'tag_name': 'v1.0.0-rc1'},
                        {'tag_name': '<script>'}, {'html_url': 'https://evil.example/download'},
                        {'published_at': None}, {'draft': 'false'}):
            with self.subTest(changes=changes):
                self.assertEqual(self.check({**self.release(), **changes})['status'], 'unavailable')

    def test_no_published_release_differs_from_network_failure(self):
        for failure, expected in ((HTTPError(updates.RELEASE_API, 404, 'Not Found', {}, None), 'unreleased'),
                                  (HTTPError(updates.RELEASE_API, 403, 'rate limited', {}, None), 'unavailable'),
                                  (URLError('offline'), 'unavailable')):
            with self.subTest(expected=expected), patch.object(updates, 'build_opener') as opener:
                opener.return_value.open.side_effect = failure
                self.assertEqual(updates.check_for_updates()['status'], expected)

    def test_truncated_response_reports_retryable_failure(self):
        with patch.object(updates, 'build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.side_effect = IncompleteRead(b'partial')
            self.assertEqual(updates.check_for_updates()['status'], 'unavailable')

    def test_response_size_and_content_are_bounded(self):
        for body in (b'x' * (updates.MAX_RESPONSE_BYTES + 1), b'not JSON', b'[]'):
            with self.subTest(size=len(body)), patch.object(updates, 'build_opener') as opener:
                opener.return_value.open.return_value = io.BytesIO(body)
                self.assertEqual(updates.check_for_updates()['status'], 'unavailable')

    def test_redirect_cannot_contact_an_unrelated_host(self):
        for url in ('http://api.github.com/metadata', 'https://api.github.com.evil.test/', 'https://user@api.github.com/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                updates._ReleaseRedirects().redirect_request(None, None, 302, '', {}, url)


if __name__ == '__main__':
    unittest.main()
