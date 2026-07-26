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
