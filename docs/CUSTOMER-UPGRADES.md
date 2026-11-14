# Customer upgrades

A Git push is not a complete customer upgrade. Track the hosted service, local
app, and installed assistant integration separately. This document distinguishes
what works now from the release work still required.

## What customers can do now

### Existing Mac source/bootstrap installations

1. Finish current work and quit Ninai and connected assistants so old server
   processes do not continue running during replacement.
2. Keep a recovery copy of the entire memory folder after those processes have
   stopped. The default is `~/.ninai`; use the actual folder if configured
   differently. Keep the database and any SQLite sidecar files together.
3. Return to [the installation page](https://ninai.io/install/), sign in, and
   download the current Mac installer. Rerun the displayed command using the same
   app installation and memory locations as before. Do not uninstall first.
4. Review connection and session-capture choices. The installer does not silently
   grant new memory access. Reopen Ninai and restart each connected assistant.
5. Verify an existing memory and its source, project access, and a fresh-session
   recall before continuing work. If setup fails, read its recovery message
   rather than repeatedly deleting or replacing folders.

Before replacement, the Mac installer now creates a private, consistent SQLite
recovery snapshot in the memory folder’s `recovery/` directory. It includes
committed WAL data and validates the snapshot. Failure stops replacement.
Snapshots are not restored over subsequent writes or removed automatically; keep
them until verification and manage their disk usage. Unattended updates preserve
the capture setting, and capture changes happen only after connector setup
succeeds. Symbolic-link database paths are rejected.

The Mac installer separates replaceable application files from memory, retains
its previous app during replacement, and restores app/configuration backups on
setup failure where possible. This is not a full database rollback system or a
verified upgrade for every historical release. The current installer builds on
the customer's Mac; signed packaged-app upgrades remain a release gate in
[MACOS-RELEASE.md](MACOS-RELEASE.md).

### Hosted service

A successful backend deployment updates the service customers connect to; it
does not upgrade a local app, install a skill, or prove that an assistant refreshed
its cached tool definitions. First restart/reload the assistant and verify tool
availability. Do not disconnect and recreate a working connection as the default
upgrade instruction: that can change its identity and require project access to
be selected again. Preserve existing grants; never silently broaden them.

### Assistant plugins, skills, and hooks

These are installed artifacts, separate from the cloud URL. Existing users need
the updated integration package and an assistant restart/reload. Updating the
backend alone cannot install a missing continuity skill or local lifecycle hook.
For Codex cloud continuity, Ninai0.1.1 includes an explicit offline installer:

```sh
~/.ninai-app/venv/bin/ninai integration-skill install --client codex
```

For another installation, run `ninai integration-skill install --client codex`.
It installs the bundled workflow in Codex's user skill directory, updates only
untouched Ninai-owned files, and refuses edited/unrelated/symlinked files or a
newer installed skill. It does not change connection credentials or memory
permissions. If a two-file update is interrupted, it stops for manual review
rather than trusting mismatched ownership metadata. No update runs in the
background. Other assistants and cloud-only setups without Ninai installed do
not gain this workflow from an HTTP URL alone; they need separate acceptance.

### Windows

There is a preview installer. Native Windows Server 2022 CI has passed unsigned
installation and prior-version upgrade/data-preservation regression. Clean
Windows 11 user-interface, owner-verification and trusted-signature acceptance
remain incomplete. Do not present it as a supported production upgrade route.
See [WINDOWS-PREVIEW.md](WINDOWS-PREVIEW.md).

## Update checks now implemented; signed installation remains pending

The app’s **Help & feedback → Updating Ninai and recovering data** section
shows the running package version and an explicit **Check for updates** action.
It fetches only public GitHub release metadata, with bounded response size and
network timeout; no memories, project names, credentials, or prompts are sent.
It distinguishes current, newer, unpublished, development-ahead and failed checks.
Offline or failed checks never report that the app is up to date. Release links
are constrained to this repository. No request runs automatically on startup.

The checker offers release notes and a manual guide. It does not download,
execute, install, or verify a signed artifact. Package and plugin versions are
now `0.1.2`; this is a code version, not proof of a signed public release. The cloud setup explains the explicit Codex skill-install command. Showing
installed integration versions separately and a complete cloud-only novice
installation flow remain open work.

Offer **Update and restart** only after a platform has a tested, signed update
artifact and recovery mechanism. Use immutable versioned releases and verified
release metadata; a moving `main` archive is not a reliable release identity.

Before replacement: finish active work, create a consistent database backup,
validate artifact integrity/platform, and preserve settings and client identity.
After replacement: run diagnostics and a bounded memory/source/access check,
refresh supported assistant integrations, and clearly report any remaining
manual restart. A successful file copy is not a successful upgrade.

Retain a known-good app and backup until validation completes. Keep schema
changes backward compatible across the supported rollback window; do not restore
an older database over newer user writes automatically. A failed migration or
incompatible downgrade must stop with a recoverable explanation.

## Acceptance before advertising seamless upgrades

- Upgrade a real prior installation with memories, sources, projects, grants,
  capture preferences, and audit history; verify all remain intact.
- Test separate/custom memory locations, spaces in paths, repeated runs,
  unavailable network, corrupt/incorrect-platform artifacts, denied permissions,
  interrupted replacement, and insufficient space.
- Inject failures during installation, migration, app build, and connector repair;
  prove recoverability without deleting or exposing memory.
- Start fresh assistant sessions after upgrade. Test natural recall, durable save,
  continuity, review-only permissions, and revocation—not merely tool presence.
- Verify old supported clients against the new cloud service and existing access
  tokens/grants. Confirm cached connector metadata refresh on actual hosts.
- Test on real Mac and Windows systems with standard-user permissions. Record
  package signing, provenance, version, and evidence for each accepted platform.

The natural-prompt gate is documented in
[IMPLICIT-CONTINUITY-ACCEPTANCE.md](IMPLICIT-CONTINUITY-ACCEPTANCE.md).

## Packaged development regression tooling

Isolated packaged build, Mac prior-vault smoke, Windows bundled preview installer,
and native Windows installer-regression workflow are now prepared. See
[MACOS-RELEASE.md](MACOS-RELEASE.md) and [WINDOWS-PREVIEW.md](WINDOWS-PREVIEW.md)
for exact commands and limits. Unsigned/ad-hoc CI artifacts do not establish
publisher identity or complete the signed customer upgrade gate. The workflows
never publish installers or broaden assistant grants. Mac app replacement and
Windows native UI/clean-machine acceptance remain explicit manual gates.
