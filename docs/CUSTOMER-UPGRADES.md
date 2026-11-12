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
Ninai does not yet provide a unified customer-facing integration updater.

### Windows

There is a preview installer, but Windows install/upgrade/rollback has not been
accepted on a real clean Windows machine. Do not present it as a supported
production upgrade route. See [WINDOWS-PREVIEW.md](WINDOWS-PREVIEW.md).

## Required product flow — not implemented yet

The app needs an **App updates** view showing the installed version/build,
latest supported release, release notes, and whether the assistant integration
also needs updating. Start with an explicit **Check for updates** action; do not
send memories, project names, or prompts in an update request. Offline or failed
checks must say “could not check”, not “you are up to date”.

Offer **Update and restart** only after a platform has a tested, signed update
artifact and recovery mechanism. Until then, show the accurate manual route.
Use immutable versioned releases and authenticated/signed release metadata;
a moving `main` archive is not a reliable release identity. Record installed
build and integration versions. Current packages and the plugin still use
`0.1.0`, so publishing changed contents under that same version is insufficient
for reliable update detection.

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
