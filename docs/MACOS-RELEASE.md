# Ninai macOS release

Ninai local mode is a macOS application backed by a SQLite vault stored in the
user's home directory. It is independent from the hosted PostgreSQL product and
never uploads or synchronizes the local vault automatically.

## Build the application

Run on macOS with Python 3.11 or newer:

```bash
./scripts/build-macos-app
```

The build creates `dist/macos/Ninai.app` and `dist/macos/Ninai-macOS.zip`. The
application contains the Python runtime, owner UI, engine code, and web assets;
SQLite itself is provided by the bundled Python runtime. The user's database is
created on first launch under `~/.ninai/` and is not embedded in the release.

## Customer release gate

An unsigned development build is not a customer installer. Before attaching the
ZIP to a GitHub release or linking it from `ninai.io`:

1. Build on the intended Apple Silicon or universal release runner.
2. Sign the app with a Developer ID Application certificate.
3. Submit it to Apple's notarization service and staple the ticket.
4. Verify it on a clean Mac with Gatekeeper enabled.
5. Run remember, recall, provenance, permission-revocation, and disclosure tests.
6. Publish the checksum and attach the notarized ZIP to a versioned GitHub release.

Signing requires the release owner's Apple Developer account, certificate, and
notarization credentials. Those secrets must remain in a protected release
environment and must never be committed to this repository.

## Product boundary

The macOS app is for local customers. ChatGPT and Claude.ai connect to the
public hosted MCP endpoint and therefore use the cloud dashboard and PostgreSQL
vault. They cannot directly connect to or silently read this private SQLite
database.

## Isolated build and owner signing workflow

Use output folders outside the installed app and vault. Neither command below
replaces an installed app or changes assistant configuration:

```sh
NINAI_BUILD_DIR=/tmp/ninai-build NINAI_DIST_DIR=/tmp/ninai-dist ./scripts/build-macos-app
engine/.venv/bin/python scripts/test-macos-bundle-upgrade.py /tmp/ninai-dist/Ninai.app
```

The smoke exports immutable prior source `8eb5224ce2c7023ad52ad42e7563c446c10e3b3f`
(0.1.0), creates synthetic memories, provenance, access grants, audit history and
capture settings in a disposable home/vault, launches the actual frozen app, and
checks preservation. It terminates only the process it launches. This proves a
bounded startup/data smoke, not visual, assistant-host, or signed upgrade acceptance.

Without credentials the builder creates an explicitly ad-hoc development ZIP.
`.github/workflows/desktop-installers.yml` builds development artifacts only and
never signs, notarizes or publishes them. Missing signing credentials never turn
an unsigned build into a customer release.

For a release owner with Apple Developer membership:

1. In Keychain Access, create a certificate signing request. Keep its generated
   private key on the owner's Mac; do not export or share it.
2. The Apple account holder creates a **Developer ID Application** certificate
   in Certificates, Identifiers & Profiles using that request. Download/open the
   certificate and verify `security find-identity -v -p codesigning` lists it.
3. In the owner's Terminal run `xcrun notarytool store-credentials Ninai-release`
   and answer its prompts directly. Never put the password, API key, certificate
   private key, or credentials in this repository or chat.
4. Build into a fresh isolated output directory with the full certificate name:

```sh
NINAI_CODESIGN_IDENTITY='Developer ID Application: OWNER (TEAMID)' \
NINAI_BUILD_DIR=/tmp/ninai-signed-build NINAI_DIST_DIR=/tmp/ninai-signed-dist \
./scripts/build-macos-app
./scripts/notarize-macos-app /tmp/ninai-signed-dist/Ninai.app Ninai-release
```

PyInstaller signs collected binaries using the selected identity. The release
gate refuses ad-hoc signatures and missing hardened runtime, verifies all nested
code, submits to Apple, staples and validates the ticket, checks Gatekeeper, then
repackages the stapled app as `Ninai-macOS-notarized.zip` with a SHA-256 checksum.
The archive before stapling is not the release artifact. A checksum detects
corruption; publisher trust comes from Developer ID and notarization.

Do not replace a running customer app. After signed clean-machine acceptance,
quit Ninai and assistants, take a consistent vault recovery copy, retain the old
app, and manually replace the app only. Restart and check existing provenance,
projects, grants, capture settings and audit history. Keep the recovery copy and
old app until acceptance completes; never restore an older database over newer
writes automatically. Automatic signed installation remains unimplemented.

References: [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution),
[Apple distribution checks](https://help.apple.com/xcode/mac/current/en.lproj/dev033e997ca.html).
