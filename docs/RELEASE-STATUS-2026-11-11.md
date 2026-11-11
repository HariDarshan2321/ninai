# Release status — 11 November 2026

The updated onboarding is deployed and available for guided Mac source-install
testing. Full production readiness is not established.

## Verified deployment

- Onboarding commit: `d12b30dbb6154cccb9cbf192efb8454eca8312a7`, pushed to main.
- [GitHub Actions run](https://github.com/HariDarshan2321/ninai/actions/runs/43029946204): engine, website and cloud jobs all passed.
- Cloud job ran 107 tests, including database integration tests; the log has no
  missing-database skip. Engine ran 79 tests plus the 12-check local transport
  journey. Website dependency audit reported zero vulnerabilities.
- [Vercel deployment](https://vercel.com/darshans-projects-a4372b06/ninai/6GbVmbevR7KRQjEZu5vbeSST6kq4): successful for that exact commit.
- [Public installation page](https://ninai.io/install/): HTTP 200 with the real
  interactive walkthrough and truthful Mac/Windows distribution status.
- Public video, caption file, poster and chapter manifest returned HTTP 200 and
  matched the pushed assets byte for byte.
- Browser verification: chapter 6 seeks to 35.114 seconds; playable video duration
  74.648435 seconds, one caption track, no broken page images.
- `https://app.ninai.io/health` and `/ready` returned HTTP 200. `/control/login`
  returned HTTP 302 to the configured Auth0 host. These are anonymous availability
  checks, not completion of signup, tool consent, or authenticated memory access.
- Those endpoint observations do not establish an always-on hosting plan or
  eliminate cold starts after inactivity.

Follow-up product language cleanup accompanies this report: memory areas replace
internal scope labels in filters/editing/badges; storage paths are behind a
disclosure; the public memory label no longer suggests automatic privacy
classification; sharing-history text describes stored IDs and estimated tokens
rather than promising a historical copy of the exact packet. Local engine and
protocol acceptance passed again after these changes. Use the current main
commit's checks for the final follow-up deployment status.

## Release blockers requiring external evidence

1. No Developer ID Application signing identity is available on this Mac.
   Signing/notarization needs the release owner's Apple Developer identity in
   Keychain or protected CI. Do not send signing secrets through chat. The source
   installer still requires Python 3.11+ and builds on the user's machine.
2. No signed Windows package or real Windows-device acceptance is recorded.
3. A clean-machine independent beginner test has not established five-minute
   setup. The Mac was locked during further native GUI interaction.
4. Full current production signup/OAuth, connection, write, recall and revoke
   still needs a designated tester. No production accounts were accessed here.
5. Confirm current hosting plan, inactivity behavior, alert delivery, and the
   production restore drill with the service owner. Endpoint 200s are insufficient.
6. The installed-build real Codex run hit its usage limit before revocation.
   Source real-host acceptance and installed model-free protocol acceptance
   passed; the incomplete installed model run is not marked passed.
7. Actual authenticated Cursor/VS Code agent tests remain pending by the user's
   explicit choice. Configuration and real protocol subprocesses were tested.

## Partner feedback scope

Invite a small guided Mac test using non-sensitive sample decisions and one
already-installed Claude Code or Codex assistant. Make the Python prerequisite
clear before asking a non-technical tester to install. Collect their OS/assistant
version, time to first recalled decision, where they needed help, and a screenshot
of any error without credentials or private memories. Do not advertise Windows,
universal assistant compatibility, a signed one-click installer, or production
security certification.

This report records evidence, not a message sent to Vanessa or a public post.
