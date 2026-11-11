# Onboarding acceptance — 11 November 2026

Decision: ready for a joint local review. This is not public-launch approval.
No deployment, publishing, messages, or production-account changes were made.
All acceptance data was synthetic, in separate temporary installations/vaults or
the existing disposable `ninai-acceptance-20261109` Docker project.

## Changes prepared locally

- Real-screen setup video, chapters, captions, transcript and checklist on the
  installation page; observational four-step setup guide inside the app.
- Copyable requests for recall and revocation. Revocation explicitly requires a
  fresh tool call rather than repeating the assistant's remembered answer.
- Setup verification retains earlier successful recall beyond 100 newer log
  entries. Indexed project/client queries avoid loading the entire history.
- Other memory areas start collapsed when no Read grants exist. Existing Read
  grants keep that section expanded, with the grant count visible on each card.
- Home accurately describes disabled capture. Setup-guide failures offer retry
  without replacing the saved-memory list.
- New `scripts/verify_local_setup.py` runs a disposable desktop/API-to-MCP journey
  using whichever installed Python interpreter launches it. It never changes
  global assistant configuration or opens an existing vault.
- CI is configured to run this protocol journey and provide PostgreSQL for cloud
  tests. The workflow YAML was parsed locally; remote CI has not run for these
  unpushed changes.
- `cloud/uv.lock` was synchronized by uv with existing package metadata (MCP upper
  bound and the already-declared psycopg pool extra). `uv lock --check` passes.

## Evidence collected

| Check | Result | Boundary |
| --- | --- | --- |
| Engine suite | 79 passed | Includes installer/config isolation and real editor-config subprocess transport; not authenticated editor agents |
| Cloud suite | 107 passed, zero skips | Disposable local PostgreSQL 16 |
| Hosted HTTP | Six checks passed | Localhost PAT transport, not production OAuth |
| Website | Typecheck, production build and validator passed | No deployment |
| Real Claude Code/Codex, source interpreter | Full handoff/revocation/peer continuity passed | Synthetic project, per-invocation connection configuration |
| Fresh Mac source installation | Built, ad-hoc signed, opened updated native app | Existing development machine; not signed/notarized distribution |
| Real Claude Code/Codex, freshly installed interpreter | Both wrote and recalled peer memories | Codex hit its usage limit before the revocation tool call; this run is incomplete |
| Installed protocol acceptance | 12 checks passed | Actual MCP subprocesses; no model or editor authentication |
| Browser product journey | Create named project, save, grant only Read, recall with source, revoke, denied fresh request, verified guide | Actual desktop assets/API/SQLite with disposable data, not a native GUI test |
| Video/assets | Correct chapter seek to 35.114s; duration 74.648435s; caption track; no broken images | Walkthrough starts after installation |
| Layout | Desktop inspected at 1280×900; install page measured at 390px with no horizontal overflow | No claim of mobile desktop-app support |
| Native UI | Updated guide rendered in installed app | Further interaction blocked because the Mac was locked |

Local evidence files:

- Engine: `/tmp/ninai-engine-tests-2026-11-11.log`
- Cloud: `/tmp/ninai-cloud-tests-2026-11-11.log`
- Installed protocol check: `/tmp/ninai-installed-setup-2026-11-11.log`
- Browser screenshot: `/tmp/ninai-onboarding-review-2026-11-11.png`
- Source real-host run: `/var/folders/6x/8p3927h171s5rzgrvtrtcw340000gn/T/ninai-real-host-ikx9cbzl`
- Installed partial real-host run: `/var/folders/6x/8p3927h171s5rzgrvtrtcw340000gn/T/ninai-real-host-7t9h16ov`
- Fresh app and install log: `/var/folders/6x/8p3927h171s5rzgrvtrtcw340000gn/T/ninai-final-review-g1vm2l4q`

These paths are temporary local evidence, not distributable artifacts.

## Joint review before inviting users

1. Unlock the Mac and complete the native app journey with a fresh named project.
   Time the attempt; record any step that needs explanation or a terminal.
2. Re-run the installed real-host revocation/continuity gate once Codex usage is
   available. Protocol acceptance does not replace this missing model step.
3. Try the guide as a beginner: find a connection, save one decision, recall it
   with its source, and revoke access. Check the video and captions alongside it.
4. Review the exact source-install prerequisites with Vanessa before choosing a
   technical private-test audience. Do not advertise a five-minute beginner
   installation without independent clean-machine evidence.

## Remaining public-release gates

- Developer ID signed/notarized Mac package and clean-machine installation.
- Signed Windows package and an actual Windows device test.
- Independent beginner timing; no five-minute claim is established.
- Current real hosted signup/OAuth and create/write/read/revoke journey.
- Release-owner confirmation of always-on hosting, plus alert and recovery
  evidence. No hosting plan or production settings were changed here.
- Cursor and VS Code authenticated agent invocation remain pending by the
  user's explicit choice. Their generated configurations/protocols were tested.

Local memory is not encrypted by Ninai; labels are not encryption. Local and
hosted memory remain separate, with no automatic sync. Revocation blocks future
disclosures and cannot retract text already received by an assistant.
