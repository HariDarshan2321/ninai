"""Explicit, metadata-only release checks. Never installs or executes downloads."""
from __future__ import annotations

import json
import re
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import __version__

RELEASE_API = 'https://api.github.com/repos/HariDarshan2321/ninai/releases/latest'
RELEASE_PREFIX = 'https://github.com/HariDarshan2321/ninai/releases/tag/'
GUIDE_URL = 'https://github.com/HariDarshan2321/ninai/blob/main/docs/CUSTOMER-UPGRADES.md'
MAX_RESPONSE_BYTES = 256 * 1024


class _ReleaseRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != 'https' or target.netloc != 'api.github.com':
            raise ValueError('Unexpected release metadata redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _version(value: object) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(r'v?(0|[1-9]\d{0,8})\.(0|[1-9]\d{0,8})\.(0|[1-9]\d{0,8})', value):
        raise ValueError('Unsupported release version')
    return tuple(int(part) for part in value.removeprefix('v').split('.'))


def check_for_updates() -> dict:
    """Run only on a user action. No vault, identity, credentials or telemetry sent."""
    result = {'installed_version': __version__, 'latest_version': None,
              'release_url': None, 'guide_url': GUIDE_URL}
    request = Request(RELEASE_API, headers={'Accept': 'application/vnd.github+json',
        'User-Agent': f'Ninai/{__version__}', 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with build_opener(_ReleaseRedirects()).open(request, timeout=5) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError('Release metadata is too large')
        release = json.loads(raw)
        if not isinstance(release, dict) or release.get('draft') is not False or release.get('prerelease') is not False:
            raise ValueError('Expected a published stable release')
        tag = release.get('tag_name')
        latest, installed = _version(tag), _version(__version__)
        expected_url = RELEASE_PREFIX + tag
        if release.get('html_url') != expected_url or not release.get('published_at'):
            raise ValueError('Unexpected release metadata')
        result.update(latest_version=tag.removeprefix('v'), release_url=expected_url)
        if latest > installed:
            result.update(status='update_available', message='A newer release is published. Review its notes and supported installation steps before updating.')
        elif latest == installed:
            result.update(status='current', message='You have the latest published stable version. Assistant integrations may need their own update.')
        else:
            result.update(status='ahead', message='This build is newer than the latest published stable release.')
    except HTTPError as error:
        if error.code == 404:
            result.update(status='unreleased', message='No stable release is published in the update channel yet. See the upgrade guide for the current manual route.')
        else:
            result.update(status='unavailable', message='Could not check for updates. Try again later; your app and memories are unchanged.')
    except (URLError, OSError, HTTPException, ValueError, TypeError):
        result.update(status='unavailable', message='Could not check for updates. Try again later; your app and memories are unchanged.')
    return result
