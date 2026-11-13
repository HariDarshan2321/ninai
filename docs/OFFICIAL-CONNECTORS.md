# Ninai connector packages and directory handoff

Prepared 13 November 2026. These are Ninai-authored packages for supported hosts. No directory approval, endorsement, public submission, publication, or current production acceptance is asserted. Earlier developer-mode read tests in the existing submission kit do not replace a complete reviewer-account run.

## Build and local verification

From the repository root, run:

```sh
python3 scripts/build_official_plugins.py --check
python3 scripts/build_official_plugins.py
python3 -m unittest discover -s scripts -p 'test_official_plugins.py' -v
claude plugin validate ./plugins/ninai
```

Outputs are `dist/plugins/ninai-openai-0.1.2.zip` and `dist/plugins/ninai-claude-0.1.2.zip`, each with a SHA-256 sidecar. ZIPs use fixed timestamps, stable ordering, regular-file permissions, and no credentials. Rebuild them after changing the source; `dist/` is intentionally ignored.

OpenAI's ZIP contains root Agent Plugins manifests plus the Codex compatibility overlay. Its inline OpenAI extension is canonical; the fallback is not merged by the host. Claude's ZIP contains `.claude-plugin/plugin.json` and `.mcp.json`; it excludes the OpenAI manifests. Both bundle the same continuity skill, README, license, and website assets. Claude's required 512px PNG is a direct rasterization of the website SVG, not a replacement mark. Vault `#0B302B` and Permit `#DCEF7B` supply the listing colors; both pass the relevant 2:1 contrast check. The unchanged wordmarks remain available for review materials; the square app icon is used for directory icons.

The local validator covers metadata limits, paths, secret-field exclusions, version alignment, transport/auth declarations, exact website SVG equality, review-case completeness, icon dimensions, and archive integrity. It does not emulate a directory security scan or make a runtime availability claim. The current upstream Agent Plugins 1.0.0 MCP JSON schema rejects server extensions even though OpenAI's package guide documents `extensions.com.openai.auth`. Therefore the documented OAuth overlay is retained: the generic schema can validate the portable core after removing only that overlay, while the local validator checks the exact OAuth/DCR overlay separately. Do not describe that as an unmodified full-schema pass.

## Private installation and update review

Claude Code can inspect the source without a marketplace using `claude --plugin-dir ./plugins/ninai`. In Claude chat or Cowork, upload the Claude ZIP through Customize → Plugins → Add → Upload plugin; then connect Ninai on the plugin's Connectors tab. Neither operation publishes a directory listing.

For Codex/ChatGPT local testing, add the source folder to a supported repo or personal plugin marketplace and install from that source in the desktop directory. After an offline source update, rebuild the package or refresh the selected local marketplace and restart the host so it loads the updated skill; a remote MCP URL alone does not update or install the skill. Installing or refreshing the package does not authenticate an account or grant memory access. This handoff makes no claim that a public repository/tag already contains these changes; select a real published revision only after release-owner review.

Connect through Ninai OAuth, bind the connection at https://app.ninai.io/control, and explicitly grant a project. A new connection has no project access. This is the opt-in hosted PostgreSQL vault: the package never uploads or reads the local SQLite vault. A connection does not guarantee that every model turn triggers retrieval or capture.

## OpenAI submission

Portal: https://platform.openai.com/plugins. Choose the owner organization/project and verified developer identity, then upload the OpenAI ZIP with its MCP server present from the first upload. The submitter needs organization ownership or Apps Management Write. Use the remote **With MCP** flow.

Prepared listing values are in `plugin.json` under `extensions.com.openai.interface`: name Ninai; subtitle “Memory for your project work”; category Productivity; publisher Ninai; project-continuity description; Search/Write capabilities; starter prompts; website, support, privacy and terms URLs; square icon; light/dark colors. The verified identity controls the directory publisher name. Confirm every URL, especially the newly prepared support page, is deployed and accessible before uploading.

MCP setup uses https://app.ninai.io/mcp with OAuth/DCR discovery. Public protected-resource discovery returned the matching resource and Auth0 authorization-server URL during this packaging pass; a reviewer-account authorization and all-tool run remain pending. Never place a PAT or OAuth client secret in a ZIP or headers. The portal's API-key connection limitation is not solved by putting a token in a manifest.

The package includes exactly five positive and three negative review cases and release notes. Cases are a review plan, **not execution evidence**. Run all cases with the dedicated synthetic reviewer workspace described in [DIRECTORY-SUBMISSION-KIT.md](DIRECTORY-SUBMISSION-KIT.md). Complete these owner steps:

1. Provide verified publishing identity, domain ownership, and a dedicated reviewer account. Place credentials only in the protected Review details form.
2. Connect and scan the server; host the exact portal-issued token at the specified HTTPS `/.well-known/openai-apps-challenge` location without replacing another integration's challenge.
3. Execute the imported cases, preserve redacted evidence, and record an accessible walkthrough URL. The recording is intentionally omitted from the package until it exists.
4. Resolve metadata, skill and MCP findings; complete reviewer access, policy attestations, country availability and any business details in the dashboard.
5. Submit for review only after approval to do so; publish only after external approval and a release-owner decision.

## Anthropic submissions

Portal: https://claude.ai/directory/manage (new-submission entry: https://claude.ai/directory/manage/new). The paid-plan account and applicable organization role, connected GitHub write access, and policies must be checked by the owner.

**Plugin bundle source:** repository `HariDarshan2321/ninai`; plugin path `plugins/ninai`; select an actual published branch/tag after source review. No release tag has been created by this work. Submit the plugin bundle and its owned remote MCP server as **separate** submissions; the bundle does not approve the connector.

Plugin form preparation:

- Source: repository, plugin path, tracked branch/tag; Validate against the exact published commit.
- Listing details: manifest and README supply Ninai identity, description, author, MIT license, privacy URL and real icon. The README exceeds the 40-word minimum. The first portal save/submission can consume the bundled icon; later icon changes may require portal handling.
- Data handling: disclose hosted project memory, provenance and disclosure records; retention/deletion according to the actual privacy policy; no additional destination declared by this package. Do not claim a retention duration, age restriction, or organization policy that the owner has not verified.
- Compliance: contact hello@ninai.io and the four current acknowledgements require owner review.
- Review and submit: confirm details and choose webhook or scheduled updates. Keep automatic publication off unless separately authorized. GitHub webhook setup is an account/repository change and was not performed.

The repository must be public before listing publication. The current repo must also meet Anthropic's archive-size and file-count checks; a small plugin ZIP alone does not prove that the entire monorepo meets them. Portal Validate and the security/policy scan remain required.

**MCP connector form preparation:** URL https://app.ninai.io/mcp; name Ninai; one-liner “Source-backed memory for your project work”; description from the listing manifest; category Productivity (confirm portal vocabulary); documentation https://ninai.io/support/; privacy https://ninai.io/privacy/; contact hello@ninai.io; bundled square PNG. Select and verify a permanent slug in the portal rather than claiming one is available.

The remaining connector steps cover synced tools and annotations; read/write use cases and account/project-grant prerequisites; company Ninai and https://ninai.io; required OAuth sign-in; API ownership and relevant data-handling answers; private test-account instructions and confirmation every tool was tested; seven current compliance acknowledgements; final review. This package does not provide an interactive MCP App UI, so an MCP App carousel is not claimed. Supply screenshots only if the selected submission flow requires them. Do not select unverified company, health-data, sponsorship, commerce or compliance declarations merely to complete the form.

## Sources checked

These primary references govern the external steps and may change. Recheck them at handoff:

- [OpenAI package format and OAuth](https://developers.openai.com/plugins/build/plugins)
- [OpenAI upload, listing fields, review cases and publication](https://developers.openai.com/plugins/deploy/submission)
- [Agent Plugins manifest schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json) and [MCP schema](https://agent-plugins.org/schemas/1.0.0/mcp.schema.json)
- [Claude plugin structure and testing](https://claude.com/docs/plugins/build)
- [Claude pre-submission validation](https://claude.com/docs/plugins/pre-submission-checklist)
- [Claude plugin submission fields](https://claude.com/docs/plugins/submit)
- [Claude MCP connector submission fields](https://claude.com/docs/connectors/building/submission)

Remaining release blockers are external owner actions and evidence: source publication to a selected revision, deployed support URL, eligible publishing identities, reviewer account and all-tool tests, walkthrough, domain verification, directory scans/attestations, and external publication decisions. No signing certificate is needed to build these data-only plugin packages.
