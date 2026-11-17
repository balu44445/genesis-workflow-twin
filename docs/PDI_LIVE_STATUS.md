# GENESIS live PDI status

**Source-version boundary:** This report describes the installed sequential version and its historical export. Workspace 0.2 adds an uninstalled gateway/guard upgrade with local tests only; see [WORKSPACE_VALIDATION.md](WORKSPACE_VALIDATION.md) and [CONCURRENCY_UPGRADE.md](CONCURRENCY_UPGRADE.md). No results below certify that upgrade.

Updated November 16, 2026. Instance: private development PDI (hostname omitted publicly)
Actual API base: private scope identifier omitted from the public repository
Update set: **GENESIS PDI Demo**, Global

**All three main scenarios have passed live:** vulnerable self-approval, corrected self-approval rejection, and Alice → Bob → Carol completion. Anonymous access was denied on every resource, authenticated role-free access was denied on every resource, and Alice's direct Table API update was blocked. The corrected policy was re-exported after role restoration: revision `demo-fixed-1`, `require_distinct_approver=true`.

Instance statistics: **Brazil**, build date `11-03-2026_2245`, build tag `glide-brazil-08-25-2026__patch2-10-22-2026`, observed at `/stats.do`. Browser returned to administrator context and the completed request was left open.

## Installed configuration

- Standalone `u_genesis_request` with state, requester, assigned approver, approved-by, and snapshot fields.
- Active Global, server-side GenesisCore and GenesisGateway; Glide AJAX disabled. The five installed scripts were compared with the reviewed source.
- Active synthetic genesis.alice, genesis.bob, and genesis.carol, each assigned u_genesis_demo and rest_api_explorer. No administrator role or password was assigned to these actors by the agent.
- Administrator-only manifest property u_genesis.manifest.
- Three JSON REST resources requiring authentication and ACL authorization, inheriting the GENESIS REST_Endpoint execute ACL requiring u_genesis_demo.
- Table create/write/delete ACLs require admin; read allows admin and demo role. Field wildcard read requires demo role; wildcard write requires admin. Temporary security_admin elevation was removed.

These are configuration observations. Runtime results below distinguish actual enforcement checks from pending work.

## Live scenarios and persisted records

| Scenario | Actual observation |
|---|---|
| Vulnerable Alice self-approval | Create 201 → submit 200 → approve 200. Stored state approved; requester, assigned approver, and approved-by all Alice. |
| Corrected Alice self-approval | Fresh create 201 → submit 200 → approve 400. Stored state remains pending; approved-by empty; fixed snapshot and distinct-approver guard confirmed. |
| Alice → Bob → Carol | Alice create 201 and submit 200; Bob approve 200 on November 16 at 15:56:26 UTC; Carol fulfill 200 at 15:57:49 UTC. Stored state fulfilled, requester Alice, assigned approver Bob, approved-by Bob. |

Synthetic record IDs:

- Vulnerable: record identifier retained in private evidence
- Corrected rejection: record identifier retained in private evidence
- Valid completion: record identifier retained in private evidence

Each actor used REST Explorer **Send as me** while impersonated as that actor; no caller-supplied identity selected the actor. Persisted fields were independently inspected through record forms. State and identity fields were read-only for the demo actors. Screenshots: pdi-local/vulnerable-persisted.jpg, corrected-rejection.jpg, and valid-completion.jpg.

## Authentication and negative checks

| Check | Actual result / limit |
|---|---|
| Anonymous GET model, POST create, POST action | All three returned 401 with the platform response “User is not authenticated,” using a fresh HTTPS client with no credentials/cookies and no redirect following on November 16. |
| Alice approves Bob-assigned request | 400; recovered from the previously submitted Explorer response without resending. Subsequent valid Bob approval succeeded. |
| Bob repeats approval | 400; subsequent Carol fulfillment and the stored final record preserve Bob as approver. |
| Carol fulfills a pending request | 400. A later persisted reread confirmed pending and approved-by empty. |
| Carol acts on the old vulnerable snapshot after configuration changed | 400; completed Request URI was checked. A later persisted reread confirmed approved with approved-by Alice, unchanged. |
| Direct Table API PATCH as Alice | First attempt was inconclusive because its session expired. After private sign-in, an authenticated attempt to set state=fulfilled and approved-by=Alice returned **403**, “ACL Exception Update Failed due to security constraints.” A persisted reread confirmed pending and approved-by empty. |
| Authenticated user without demo role | Alice's demo role was temporarily revoked while retaining her existing Explorer access. GET model, POST create, and POST action each returned **403**, “Failed API level ACL Validation.” Her original demo role was restored and verified in the user record, then model export as Alice returned 200 with the fixed policy. |

The anonymous requests returned authentication rejection rather than an application guard error. A later persisted reread of the target request confirmed pending with approved-by empty. No created-row inventory comparison was performed for denied create calls. Generic application 400 responses do not independently identify the specific rejecting guard.

## Local verification

- November 15 fresh Python/JavaScript suite: **34 passed**, one upstream Starlette/httpx deprecation warning. Report: pdi-local/pytest-2026-11-15.xml.
- Actual vulnerable PDI export: Z3 5.4.1 found a shortest violation at depth 2 within bound 3. Local witness replay matched the recorded live final state exactly. Snapshot SHA-256: `8725d523cc351c522a128807145175187e09ba6a019e1d10cd01825fae0c2e2f`.
- Actual corrected PDI export: **no violation within bound 3**, depths 0–3. Snapshot SHA-256: `f7fe818ca099475a65436988c7d59cfe67d4e3d86ae91da0439d66aad93c2bf0`.

These bounded model checks are separate from live ServiceNow validation. They do not establish platform-wide or unbounded safety.

## Extended live validation completed November 16

| Check | Actual result |
|---|---|
| Extra caller-supplied actor/requester keys on create; actor key on action | Both returned 400. |
| Direct PATCH of requester, assigned approver, and snapshot | 403 ACL rejection. Reread all five fields: pending, requester/assigned approver Alice, approved-by empty, snapshot still fixed revision. |
| Direct Table API create | 403, ACL Exception Insert Failed due to security constraints. |
| Direct Table API delete of a disposable gateway-created request | 403, ACL Exception Delete Failed due to security constraints. Record remained readable, draft, requester Alice, assigned approver Bob, approved-by empty. Record identifier retained in private evidence. |
| Configured Bob ID references a nonexistent user | Model export 400; original manifest then restored. |
| Configured Bob inactive | Model export 400; Bob then restored active. |
| Configured Bob lacks demo role | Model export 400 as Alice; Bob's original role then restored. |
| Demo-role Alice absent from otherwise valid manifest | Model export 200; request creation 400. Temporary manifest preserved all three eligibility types by assigning requester eligibility to Bob. Original eligibility then restored. This does not isolate an action denial for an absent caller against a matching request snapshot. |
| Final restored configuration | Model export as Alice 200; exactly three original actors, fixed revision, distinct approver true. Browser returned to administrator. |

Optional follow-ups are denied-create row-inventory comparison and an absent-caller action test with a matching-snapshot fixture. Platform-level insert denials and absent-caller create rejection have been observed. No import into a second instance or concurrency test has been performed.

## Delivery package

The Global GENESIS update set was marked Complete and downloaded. Its 43 customer updates included six unrelated platform records. The curated XML package retains 37 GENESIS records and excludes the unrelated ECC policy, password-reset process, two platform properties, and two crypto key policies. All five exported scripts matched their source, REST resource authentication/authorization flags were checked, and the exported manifest retained the corrected policy.

See PDI_PACKAGE_INSTALL.md and PDI_DEMO_RUNBOOK.md. The delivery archive is dist/GENESIS-PDI-Demo.zip. The original export stays private. Target users/role assignments are not transported and source actor IDs must be remapped before target testing. Target import remains untested.

The expired-session interruption was resolved by private sign-in. No credentials were requested, entered, or saved by the agent. Alice's approved demo access and administrator browser context were restored before finishing.

## Evidence and limits

Private evidence is in ignored pdi-local/: live-results.json, anonymous-results.json, installation-checkpoint.json, instance-build.json, actors.json, the two live model snapshots and verification results, replay evidence, and screenshots including direct-write-unchanged.jpg. Response bodies and status codes were saved without Authorization headers, cookies, passwords, or session tokens. Do not save or publish Explorer request-header panels.

This is a serial synthetic demo, with no atomic concurrency guarantee, actual provisioning, or extraction of arbitrary platform workflow/ACL logic. See [PDI_SETUP.md](PDI_SETUP.md) and the remaining acceptance matrix in [PDI_SESSION.md](PDI_SESSION.md).
