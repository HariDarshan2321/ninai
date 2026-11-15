# Launch gates — 15 November 2026

Ninai is **not production ready**. Three gates below passed on synthetic data.
Four gates are still open and need the owner. All tests used synthetic
fixtures; no real memory, secret or production database was read or changed.

Checked commit: `09dcf8d`. Hosted service at check time: version 0.1.2,
revision `b94d453`, `/health` ok, `/ready` 200.

## Passed

### Backup and restore drill (synthetic)

- **PostgreSQL 17.11, disposable Docker container, loopback only.** Migrations
  and the synthetic cross-provider fixture were applied. `pg_dump` custom
  archive (66,514 bytes) was restored into a second database with `pg_restore`.
  - Equality: all 21 tables, schema and all 8 migrations match; 0 invariant
    violations.
  - Service behaviour on the restored database: the granted client recalled
    its shared and private project memories with the original source; the
    revoked client was still refused; 3 grants and 2 disclosure records were
    present.
  - The container was removed after the run.
- **PostgreSQL 15, local binaries.** `cloud/tests/test_restore_comparison.py`
  passed (8 tests). The rehearsal now also runs the service against the
  restored database and checks recall, provenance and refusal of a revoked
  client.

Limits: production runs PostgreSQL 18, which was not available locally. This
is not a restore of the hosted database. The live recovery gate in
[RESTORE-COMPARISON-ACCEPTANCE.md](RESTORE-COMPARISON-ACCEPTANCE.md) is
unchanged and needs cost approval for a separate recovery database.

### Unsigned installers and upgrade paths

- **Mac, local.** `scripts/build-macos-app` built into an isolated folder.
  `scripts/test-macos-bundle-upgrade.py` passed: a synthetic 0.1.0 vault kept
  its memories, sources, permissions, audit history, capture setting and
  projects after the 0.1.2 packaged app started.
- **Mac and Windows, CI.** `Desktop installer regression` run 43733040492
  passed both jobs on `09dcf8d`: Windows Server 2022 install, repeated
  upgrade from 0.1.0, revocation, uninstall and reinstall with a retained
  vault; macOS 15 build and upgrade smoke.

Limits, stated plainly:

- The Mac build is ad-hoc signed. Gatekeeper rejects it (`spctl`: rejected).
  The Windows installer is unsigned. Neither is signed, notarized or trusted,
  and neither is published.
- No Apple Developer membership and no Windows signing certificate are
  available, so the signed-installer gate cannot pass now. The supported Mac
  route stays the source installer from the install page.
- Clean Windows 11, SmartScreen and Defender checks were not run.

### Browser layout

All 35 browser tests passed locally (53 s). They cover the public pages and
the synthetic desktop preview at 320, 390, 768 and 1440 pixels, collapsed
assistant controls, approval failures and recovery. This is a browser preview,
not the native app.

## Open

### Native desktop app (pending, owner check)

Automated control of the desktop host is not permitted, and was not bypassed.
Read-only findings:

- The installed app reports version 0.1.2. It was built before the session
  handoff fix (`16e9d35`) and does not contain it.
- The handoff fix did not change the version number. The app's version and
  "Check for updates" therefore cannot tell these two builds apart.

Owner checklist, on a synthetic project only:

1. Open Ninai. Note the version under Help & feedback.
2. Run onboarding to the end, or confirm it does not show again.
3. Add one memory with the Add memory form. Confirm it appears with a source.
4. Open the assistant controls. Grant Read to one assistant for the test
   project. Confirm the system approval prompt appears.
5. Recall from that assistant in a new session. Then revoke and recall again;
   expect a refusal.
6. Open "Updating Ninai and recovering data". Confirm the recovery copy
   location is shown.
7. Resize the window to narrow and wide. Note any clipped or overlapping text.

### Signed installers

Blocked on owner accounts (Apple Developer membership; Windows code-signing
certificate). No purchase was made.

### Live hosted restore

Blocked on cost approval for one separate recovery database. Production was
not touched.

### Legal operator

The brand stays "Ninai". The responsible person or company is not stated on
the site. Nothing was invented. Fields the owner must supply:

1. Operator type: private person, sole trader, or company (with legal form).
2. Full legal name. For a company: the authorised representative.
3. Postal address where the operator is established (not a PO box).
4. Contact email (currently `hello@ninai.io`; confirm).
5. Only if they exist: commercial register and number; VAT ID or economic ID.
6. Whether Ninai is offered as a business activity. This decides if the
   German provider-identification duty applies at all.
7. Country of establishment, for the privacy policy's controller statement.

Reference: [DDG section 5](https://www.gesetze-im-internet.de/ddg/__5.html),
read on 15 November 2026. The GDPR text on EUR-Lex could not be loaded on that
day, so the controller-identity fields above were not re-checked against
[Article 13](https://eur-lex.europa.eu/eli/reg/2016/679/oj). This list is not
legal advice.

### Other open gates

Fresh-account signup, sustainable sign-in configuration (the login provider
still uses development keys), and a published versioned release.

Support mail: the owner reports that both Ninai mailboxes receive mail.
Sending from them is not verified.

## Owner actions

1. Run the native app checklist above and report the results.
2. Supply the legal operator fields.
3. Decide: approve the cost of one recovery database for the live restore
   test, or keep that gate open.
4. Decide: publish a versioned release so the app can report updates.
5. Decide: rebuild the installed app so it contains the handoff fix.
