# Workspace 0.2 validation — November 17, 2026

## Completed locally

- Full Python suite: **48 passed**, one upstream Starlette/httpx deprecation warning. Includes the existing verifier/replay/parity suite plus workspace, installation-plan, AI-boundary, gateway-race and public-boundary checks. The earlier private JUnit report predates the three public tests.
- Concurrent HTTP approval attempts against the same pending local request: exactly one 200 and one 409; one state/version advance. Subsequent fulfillment succeeds.
- An evidence-write failure rolls back the state/version change in the same SQLite transaction. Rejected attempts preserve state and are recorded with reasons.
- Immutable snapshots remain attached to each request and survive a new API client. Changing the loaded policy does not alter existing requests.
- Proposed-policy comparison finds the vulnerable witness and the corrected bounded result without applying changes.
- Disabled external AI rejects explicit external requests without transmission. Mock-provider tests confirm only derived anonymous facts are sent, response storage is disabled, and provider errors do not expose provider details. **No real AI call was performed.**
- The real ServiceNow JavaScript gateway/guard files passed six controlled mocked-storage scenarios: overlapping approvals admit one winner and later fulfillment works; failed state writes retain the claim and block retries; uncertain completion does not permit repeated approval; missing uniqueness metadata fails closed; changed persisted state after a claim is rejected; invalid actors cannot consume a claim. They do not emulate ServiceNow transaction isolation or establish live database behavior.
- Package wheel built and installed into a separate temporary folder. The imported module path was checked to ensure execution used the installed package, outside the source directory. Dashboard assets loaded, Alice → Bob → Carol completed locally, and the bundled CLI demo returned violation / no_violation_within_bound. No PDI or external AI calls occurred.
- The source archive includes a file manifest with SHA-256 hashes and excludes private evidence, SQLite files, environment files and the original uncurated update-set export.
- The public wrapper passed isolation across two visitor cookies, HTTPS enforcement, secure-cookie, route allowlist, synthetic-input-only, body/depth/time, external-AI, session and request-rate checks. Invalid input is rejected before session allocation. These are local application tests, not public-host load or penetration tests.

## Browser observations

- Corrected verification shows no violation within bound 3, along with the snapshot fingerprint and explicit sequential scope.
- Vulnerable verification shows Alice submit/approve, shortest violation depth 2, and matching replay. The local explanation states its evidence basis.
- Policy preview shows violation → no violation within bound and remains preview-only.
- Local Alice → Bob → Carol workflow reached fulfilled with each accepted action in the timeline.
- Corrected self-approval was rejected, remained pending at version 1, and displayed the reason in the timeline.
- A policy-switch timing issue was found during QA and corrected by disabling operations while loading and discarding results from older snapshots.
- Desktop layout inspected. At 390 × 844, document content width was 390, with no horizontal overflow; screenshot inspected. The temporary viewport was reset afterward.
- Dashboard screenshots: pdi-local/workspace-0.2-dashboard.jpg, workspace-0.2-timeline.jpg and workspace-0.2-mobile.jpg.
- The API reference uses a nonce for its trusted initialization script; the dashboard retains its stricter same-origin script policy. The API-reference route's CDN assets are separate from the disabled external AI connection. Browser security headers and nonce matching are covered by API tests.

## Pending external validation

The user selected local checks until a second PDI is supplied and requested keeping evidence local. No second-instance installation has occurred. The new claim table, uniqueness constraint, GenesisGuard and changed GenesisGateway have **not** been installed or tested on a live PDI. Follow CONCURRENCY_UPGRADE.md before deployment. The previously completed/exported PDI update set contains the earlier sequential gateway, not this upgrade.

The installed-wheel rehearsal used the existing temporary Python environment for third-party dependencies; it is not proof of installation on a completely fresh operating system. Advanced policy semantics such as delegation, amount limits and multiple approval stages remain unsupported and visible in the dashboard.

The Render/Docker deployment configuration is prepared but has not been published. No public URL, custom domain, DNS change or live HTTPS test has been performed.
