# Website wording and readiness review — 15 November 2026

## Scope

Three independent read-only reviewers checked source claims, beginner onboarding, and the live homepage, install, start, privacy, compatibility, and support pages. The live pages returned HTTP 200. The final hosted test report was the implementation evidence; private market scores and unverified competitor or legal assertions were not used as public product claims.

## Corrections prepared locally

- AI-readable `llms.txt` now distinguishes on-device memory from the separately enabled hosted workspace, instead of saying hosted storage is unavailable.
- Homepage setup describes requirements and project access. Its example states the handoff/access prerequisites and requires an assistant retrieval call rather than implying that opening Codex automatically retrieves memory.
- The install page accurately describes automatic configuration of detected supported assistants, followed by explicit project permission choices. It now links to cloud setup and the compatibility table.
- ChatGPT compatibility describes the verified private web and shared-plugin-runtime tests. Public directory release, native desktop GUI checks, and broader account/plan coverage remain unverified.
- Local privacy claims are explicitly scoped to local setup. The local page plainly states that Ninai does not add encryption to local memory files.
- Privacy and terms distinguish the authenticated installer download from the public setup guide. The effective date is 15 November 2026.
- Support explains using the same identity/sign-in method in dashboard and assistant, and reconnecting without restoring previous permissions.
- Customer-facing research references to “MVP” were removed while preserving honest research and benchmark limitations.
- The new cloud-option paragraph has its own spacing below the installer prerequisites.

## Validation

TypeScript checking and the static production build passed. All 35 browser tests passed after the final copy and spacing changes (55.9 seconds). The suite covers public pages at 320, 390, 768, and 1440 pixels, broken images, one H1, installer-button spacing, the interactive walkthrough, synthetic desktop preview alignment, collapsed assistant controls, approval failures, and recovery. The updated homepage and install page were also visually inspected in the local browser at its default desktop size. The attempted manual mobile viewport override did not change the reported page viewport, so mobile evidence is the automated test run rather than that screenshot.

Native desktop GUI verification is not represented by browser preview tests. The native app remains outside the completed visual checks.

## Owner decisions and publication boundary

The owner requested keeping the Ninai brand. No Berlin company, legal form, registered address, certification, traction, pricing, or competitor weakness was invented. The actual responsible legal operator and contact details still require owner confirmation; this is not a legal-compliance certification. Relevant primary references: [GDPR Article 13](https://eur-lex.europa.eu/eli/reg/2016/679/) and [DDG section 5](https://www.gesetze-im-internet.de/ddg/__5.html).

Fresh-account signup, trusted signed installers and upgrades, live backup restore, and sustainable OAuth registration capacity remain launch gates. The wording review does not establish overall production readiness or a guaranteed five-minute source installation.

The owner approved committing and pushing these reviewed changes on 15 November 2026, as requested in the private agent handoff. The live site must not be described as updated before deployment is separately verified.

## Email setup handled separately

The owner approved forwarding both existing Ninai mailboxes into their existing personal Gmail inbox, retaining copies in Spacemail. Both forwarding switches and keep-copy switches were verified enabled in the respective mailbox settings. No MX change, mailbox purchase, or Google Workspace purchase was performed. Successful end-to-end message delivery has not yet been tested.

The owner chose Gmail mobile IMAP/SMTP access for replies. Adding the two accounts and entering their mailbox passwords on the phone remains an owner step; no mobile send/receive success is claimed. Primary provider instructions: [Spacemail in Gmail mobile](https://www.spaceship.com/en-GB/knowledgebase/add-spacemail-to-gmail-app/). Google documents the January 2027 retirement of third-party Send-as, with forwarding still supported: [Google notice](https://support.google.com/mail/answer/17101213?hl=en).

Email account screenshots and personal forwarding destinations remain local, not in the public repository.
