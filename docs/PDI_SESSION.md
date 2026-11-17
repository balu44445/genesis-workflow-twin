# GENESIS PDI integration — working checklist

Instance: private development PDI (hostname omitted from the public repository)

**Latest status — November 16, 2026:** Installation and all three main live scenarios passed, including persisted vulnerable self-approval, corrected rejection with unchanged state, and Alice → Bob → Carol fulfillment. All three resources denied anonymous calls with 401 and authenticated role-free calls with 403. Alice's authenticated direct Table API update was denied with 403 and persisted fields stayed unchanged. Her demo role and administrator browser context were restored; the corrected model export returned 200 afterward. Instance build Brazil patch2 was recorded. See [PDI_LIVE_STATUS.md](PDI_LIVE_STATUS.md) for evidence and the unrun extended checks. Installation checkpoints below are historical, and procedure sections remain a reference rather than a claim that every acceptance check passed.

## Current installation checkpoint — after password rotation

The user reported that the exposed password was rotated. Continued using the existing Chrome session without requesting or using the replacement credential.

- Created the Global update set **GENESIS PDI Demo** using **Submit and Make Current**.
- Created standalone **GENESIS Request** (`u_genesis_request`) and saved all five required fields: state (String 20), requester/assigned approver/approved-by (references to User/`sys_user`), and snapshot (String 4000).
- Inspected each of the four generated table ACL records (create/read/write/delete). Each requires `admin`. Non-admin enforcement and field ACLs remain untested/incomplete.
- Staged **GenesisCore** (`global.GenesisCore`) in an unsaved form, with Global scope, Glide AJAX disabled, mobile callable disabled, and scope-only accessibility. The staged 4,385-character script matches the reviewed source exactly.
- No Script Include has been saved; no GENESIS REST API, demo role, synthetic account, or manifest property has been installed during this checkpoint. Their expected names were absent during inventory before setup.
- Requested confirmation before saving the custom scripts and granting synthetic demo access, as required by the browser safety policy. Remaining installation is awaiting that confirmation.

Private installation metadata and screenshots are in `pdi-local/session-status.json`, `pdi-local/table-created.jpg`, and `pdi-local/core-installation-review.jpg`. The instance release/build was not obtained because status-page navigation timed out. **No live workflow action, export, or non-admin ACL test has been run.**

## Initial source inspection and local checks

- The uploaded ZIP and Downloads copy have the same SHA-256: `0ba3591c5edde8145ad3e42fe4a1df52269c31f329e1de45f45ad2fa5f9b40b9`.
- All 37 entries (85,453 uncompressed bytes) were checked before extraction. No absolute paths, parent traversal, symlinks, or encrypted entries were found. No archive scripts ran during extraction.
- Reviewed [PDI_SETUP.md](PDI_SETUP.md), both Script Includes, all three REST resources, the extraction adapter, and local validation sources.
- Fresh local Node checks passed for vulnerable self-approval, corrected rejection with unchanged state, Alice → Bob → Carol completion, and four negative transition cases. All five supplied ServiceNow JavaScript files passed Node syntax checks. See [local results](../evidence/review/local-core-review.json).
- Chrome displayed an existing System Administrator session on the PDI. This establishes session availability only. Installation records, release/build, endpoint paths, and ACL enforcement have not been inspected.
- The archive contains a report of 34 passing Python tests. The Python suite was **not rerun** during this session; pytest, FastAPI, and Z3 are not installed in the current Python environment.

At that initial inspection, no live installation, export, workflow action, or ACL test had been performed. See [initial inspection record](../evidence/review/source-review.json). The installation checkpoint above supersedes its installation status; older local documentation and evidence remain historical records.

## Secure the account

The administrator password appeared in a previous URL. Rotate it privately and complete all password-change steps yourself. Do not paste the replacement into chat, source files, screenshots, shell commands, or evidence. The exposed credential has not been used.

Use your authenticated browser session for installation and REST API Explorer. For later external extraction, use an instance-supported OAuth bearer token or a dedicated export account with the sample role over HTTPS, entering secrets privately. Do not put credentials into URLs. The project does not provision OAuth tokens.

## Install in this order

Follow the detailed [original installation guide](PDI_SETUP.md); these are the checkpoints to record as you go. Do not assume any item already exists merely because an administrator session is available.

1. Select **Global** and a dedicated GENESIS update set. Record the instance release/build. Use admin or `web_service_admin` for REST configuration, and elevated `security_admin` when required for ACL editing.
2. Create standalone `u_genesis_request`, without extending Task. Create string `u_state` (20), references `u_requester`, `u_assigned_approver`, and `u_approved_by` to `sys_user`, and string `u_snapshot` (4000). Keep this table free of unrelated workflow or provisioning logic.
3. Create `u_genesis_demo` and active synthetic Alice, Bob, and Carol accounts. Give each this role explicitly; do not give the actors admin or `web_service_admin`. Add `rest_api_explorer` only if using Explorer. Record their distinct 32-character sys_ids privately.
4. Give `u_genesis_demo` read access to the table and its fields. Restrict direct create/write/delete and field mutation to admin. Review all matching/generated ACLs; adding one restrictive ACL does not establish that broader access has disappeared. Include `u_snapshot`, requester, assigned approver, state, and approved-by in the review. Test direct mutations as a non-admin actor.
5. Create String property `u_genesis.manifest`, editable only by administrators. Start from [vulnerable.json](../examples/vulnerable.json), replace **actor IDs only** with actual sys_ids, retain eligibility lists, and set source to `{"kind":"servicenow_export","description":"GENESIS PDI sample configuration"}`. Confirm the serialized manifest fits the snapshot field.
6. Create active Global, server-side Script Includes [GenesisCore](../servicenow/GenesisCore.js) and [GenesisGateway](../servicenow/GenesisGateway.js), with client callable disabled. Compare saved scripts with the supplied source.
7. Create Scripted REST API **GENESIS**, API ID `genesis`. Copy the **actual Base API path** displayed by the instance; do not guess the namespace. Associate a `REST_Endpoint` ACL requiring `u_genesis_demo`. Require authentication **and** ACL authorization on the API and every resource, checking inherited settings and resource overrides.

| Method | Relative path | Source |
|---|---|---|
| GET | `/model` | [resource_get_model.js](../servicenow/resource_get_model.js) |
| POST | `/requests` | [resource_create_request.js](../servicenow/resource_create_request.js) |
| POST | `/requests/{id}/actions` | [resource_action.js](../servicenow/resource_action.js) |

Use JSON request/response formats. The gateway's `GlideRecord` calls intentionally provide privileged persistence after role and identity checks. Table ACLs must still block direct writes. This is a deliberate sample boundary, not proof of arbitrary platform ACL behavior.

Official references: [resource authentication and ACL settings](https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/t_WbSvcOpRqACL.html) and [Explorer access roles](https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/t_GetStartedAccessExplorer.html). Select documentation matching the actual PDI release. Explorer access is separate from authorization to GENESIS.

## Live workflow validation

Run one request/action at a time. Before each actor change, confirm the current impersonated identity in the UI. Do not substitute administrator calls or send `actor`/`requester` in a request body. The gateway uses `gs.getUserID()`.

Let `BASE` mean the actual GENESIS Base API path. Response data may be wrapped in `result`; inspect the actual body. Successful action resources are expected to return HTTP 200; create explicitly returns 201. Record actual codes and persisted fields, not just the absence of an error.

### Vulnerable policy

Keep `require_distinct_approver: false` and revision `demo-vulnerable-1`.

1. As Alice, POST `BASE/requests` with `{"assigned_approver":"<ALICE_SYS_ID>"}`. Expect 201, draft, requester Alice, assigned approver Alice, approved-by empty. Save request ID **V**.
2. As Alice, POST `BASE/requests/V/actions` with `{"action":"submit"}`. Expect pending.
3. As Alice, POST the same endpoint with `{"action":"approve"}`. Expect approved and approved-by equal to requester. Read the persisted record and capture this intentional synthetic violation.

### Corrected rejection

As admin, set `require_distinct_approver: true` and revision `demo-fixed-1`. Export the new model when extraction is configured. A local bounded check should report no violation within bound 3; it does not establish platform-wide safety.

1. As Alice, create a **new** request assigned to Alice. Save ID **R** and submit it.
2. As Alice, approve **R**. Expect HTTP 400 from the transition guard.
3. Read **R** after the failed call. It must remain pending with approved-by empty. A 400 by itself is insufficient: the response is generic and could also indicate bad configuration or identity.

### Alice → Bob → Carol

1. As Alice, create a **new** request assigned to Bob. Save ID **H**, then submit it.
2. As Bob, approve **H**. Expect approved, requester Alice, approved-by Bob.
3. As Carol, fulfill **H**. Expect fulfilled, requester Alice, assigned approver Bob, approved-by Bob. Verify persisted fields.

Changing the manifest invalidates subsequent actions on older requests by exact snapshot comparison. Do not reuse **V** to test the corrected guard. Use fresh requests for independent negative checks as needed.

## Authentication, ACL, and guard acceptance matrix

Use [PDI_LIVE_STATUS.md](PDI_LIVE_STATUS.md) and pdi-local/live-results.json for actual outcomes. This matrix describes acceptance criteria, not a completion claim.

| Check | Required observation |
|---|---|
| Anonymous calls to each GENESIS resource | Platform denies access before the resource runs; capture actual status/body and confirm no mutation. An authenticated browser session cannot establish anonymous denial. |
| Authenticated non-admin without `u_genesis_demo`, each resource | Platform endpoint authorization denies access; no mutation. Do not grant Explorer access just to make this test pass; use a separate authenticated external client if needed. |
| Demo-role user absent from manifest | Request creation/actions rejected; no mutation. `/model` is role-authorized and is not restricted to configured actors by these scripts. |
| Wrong actor attempts approval | Rejected; state and approved-by unchanged. |
| Carol fulfills before approval | Rejected; record unchanged. |
| Bob repeats approval on an already approved request | Rejected; record unchanged. |
| Caller supplies `actor` or `requester` alongside the allowed body key | Rejected by strict body shape; no mutation. |
| Alice edits state, approved-by, requester, assigned approver, or snapshot via form/Table API | Mutation denied; re-read every attempted field to prove it stayed unchanged. HTTP status alone is insufficient. |
| Alice creates/deletes through direct form/Table API | Denied; no created/deleted row. Use disposable test data. |
| Configured user missing, inactive, or missing demo role | `/model` returns the resource's generic 400 rejection. Change only disposable setup, then restore it and confirm a valid export. |
| Manifest changed after request creation | Old-request action rejected with no mutation; new requests use the new snapshot. |

For anonymous and role-free calls, a generic gateway HTTP 400 is **not** evidence that the endpoint ACL works. Diagnose authentication/ACL enforcement separately. Authentication policies may affect the exact denial status; preserve the real response and do not label timeouts, HTML login redirects, or unavailable-instance pages as passed ACL tests.

## Record evidence privately

Store live exports, request IDs, actor sys_ids, redacted responses, and screenshots under `pdi-local/` (ignored by version control). Never save Authorization headers, session cookies, passwords, or tokens. For each check record:

- Time with timezone, release/build, actual endpoint/method, effective actor, and manifest revision.
- Synthetic request body, HTTP status, redacted response, and before/after persisted fields.
- Outcome: NOT RUN, PASS, FAIL, or INCONCLUSIVE, with a reason and evidence filename.

For model extraction use the existing `genesis.cli extract` over HTTPS with private authentication as described in [PDI_SETUP.md §5](PDI_SETUP.md#5-read-only-extraction-from-python). Save vulnerable and corrected snapshots/evidence under separate filenames in `pdi-local/`, verify each at bound 3, and replay only the matching vulnerable witness. Never relabel an offline fixture as a live export.

Keep historical local evidence separate from live evidence. Node checks do not validate GlideRecord, ServiceNow REST wrapping, ACLs, or the installed JavaScript engine. This gateway is for a serial synthetic demo; it has no atomic concurrency protection, does not extract arbitrary Flow Designer logic, and provisions nothing.

## Next checkpoint

Preserve completed demo records and the corrected policy. Extended identity/snapshot write, direct create/delete, strict-body spoofing, missing/inactive/missing-role population, and absent-caller create checks have now passed live. All temporary actor/policy changes were restored and model export returned 200. The update set is Complete and the curated installation package and repeatable runbook are available. See PDI_LIVE_STATUS.md for observations and the optional remaining checks; target-instance import has not been tested.
