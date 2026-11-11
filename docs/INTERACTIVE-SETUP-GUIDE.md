# Interactive setup guide

The old installation concept video used text cards. It is replaced with a
75-second narrated capture of the actual local product interface, using only
synthetic sample data. It demonstrates project creation, a saved decision,
explicit Read access, real Codex recall, revocation, and sharing history.

The video is a product setup walkthrough after installation. It does not claim
to record a signed package installation. Mac setup still builds from source and
requires Python; signed/notarized distribution is pending.

The installation page has clickable chapters, English captions and transcript,
an opt-in pause after each chapter, and a browser-local checklist. Checklist
marks are user-reported and never confirm a working connection or grant access.

The app's Setup guide instead observes real project memories, permissions and
disclosure records. It never creates a test disclosure or grants access itself.
Recall verification requires a successful recall for the selected project and
assistant. Revocation verification requires a prior successful read and a denied
request after that project's Read grant was revoked. Re-enabling Read removes
the current revocation-verification state. Old logs without project IDs are not
guessed into a project. This is an additive SQLite audit migration.

Recording evidence: sample project `199d0f98-dac5-53e1-9315-c58fde448f6d`,
Codex actual `recall` returned the saved reversible-migration decision with
`app://manual`; a second actual Codex request after revocation returned empty
facts. Model calls ran between captured scenes; waiting is edited. Footage is
assembled from sequential actual browser captures, not generated UI or fake
cursor motion. Narration uses an installed system voice.

Rebuild on macOS with FFmpeg installed:

```sh
python3 scripts/build-install-walkthrough.py /path/to/actual/capture.json
```

The capture input contains chronological screenshots and chapter boundaries.
The builder generates MP4, JPG poster, VTT captions and exact chapter metadata
under `website/public/assets`. The compatibility wrapper
`scripts/build-install-video-preview` now requires real capture input and no
longer creates concept slides.

Verification: 79 engine tests pass, including observational progress and
cross-project/client negative cases. Website typecheck, static build and
validator pass. Browser checks cover actual video seeking, captions, playback,
chapter-boundary pausing, checklist/reset and the real local setup guide.

The app now offers a copyable request in both recall and revocation chapters.
The revocation request explicitly asks for a fresh tool call, so an assistant's
cached answer is not confused with a new disclosure. Verification searches the
selected project's complete history using an index; it does not forget the
successful handoff after 100 subsequent requests. Optional non-project memory
areas start collapsed when no Read grants exist, and Home explains when session
capture is off. Setup-guide failures have a retry action without hiding memories.

Run the repeatable, model-free setup acceptance against an installed interpreter:

```sh
/path/to/installation/venv/bin/python scripts/verify_local_setup.py
```

This uses a disposable vault and real MCP subprocesses. It checks default denial,
independent Read/Save/Delete permissions, source-backed recall, project/client
isolation, immediate revocation and continued access for the other client. It
does not verify authentication or consent inside an assistant application. The
engine CI job runs it; the cloud CI job now supplies disposable PostgreSQL so its
17 database integration tests cannot be silently skipped for lack of a database.
