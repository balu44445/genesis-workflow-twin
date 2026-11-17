# GENESIS repeatable PDI demo

Use a development instance and synthetic actors. Allow about 10–15 minutes once setup is complete. The validation hostname and API scope are omitted from this public repository. On another instance, copy its displayed Base API path.

## Preparation

1. Sign in privately as administrator. Keep credentials out of URLs, chat, screenshots, and saved responses.
2. Confirm Alice, Bob, and Carol are active and have explicitly assigned `u_genesis_demo` and `rest_api_explorer`, without admin. Their manifest eligibility is Alice=requester+approver, Bob=approver, Carol=fulfiller.
3. Confirm table create/write/delete and field write ACLs require admin, while demo users can read. Confirm authentication and the demo-role endpoint ACL on every resource.
4. Use REST API Explorer, JSON, and **Send as me**. Confirm the profile identity after every impersonation. Save status codes and response bodies, excluding request headers and tokens.
5. Use a fresh request for each scenario. The manifest is snapshotted per request; changing it invalidates actions on older snapshots.

## Scenario 1 — demonstrate vulnerable self-approval

As admin, save manifest revision `demo-vulnerable-1`, with `require_distinct_approver=false`. Export GET `/model` and confirm the saved values.

As Alice:

1. POST `/requests` with `{"assigned_approver":"<Alice sys_id>"}` → 201, draft. Record the returned request ID.
2. POST `/requests/<id>/actions` with `{"action":"submit"}` → 200, pending.
3. POST the same action endpoint with `{"action":"approve"}` → 200, approved.
4. Open the stored record: requester, assigned approver, and approved-by must all be Alice. This is the intentional synthetic violation.

## Scenario 2 — corrected self-approval rejection

As admin, save revision `demo-fixed-1`, with `require_distinct_approver=true`. GET `/model` must confirm the corrected policy.

As Alice, create a **new** self-assigned request, submit it, and attempt approval. Expect 201 → 200 → 400. Open the stored record: it must remain pending, with approved-by empty and the fixed snapshot.

## Scenario 3 — Alice → Bob → Carol

1. As Alice, POST `/requests` with Bob's sys_id as assigned approver → 201. Submit → 200 pending.
2. Impersonate Bob and reload Explorer. Approve the saved request → 200 approved, approved-by Bob.
3. Impersonate Carol and reload Explorer. Fulfill → 200 fulfilled.
4. Open the stored record: requester Alice, assigned approver Bob, approved-by Bob, state fulfilled.

## Access and failure demonstrations

Expected results observed on this PDI:

| Attempt | Result |
|---|---|
| Each endpoint without authentication | 401, platform authentication rejection |
| Each endpoint as authenticated Alice temporarily without demo role | 403, API-level ACL validation failure |
| Alice directly inserts, updates, or deletes through Table API | 403, ACL security constraint |
| Caller adds actor/requester identity keys to a GENESIS request | 400 |
| Export with a missing, inactive, or role-less configured actor | 400 |
| Demo-role Alice omitted from an otherwise valid manifest | Model GET 200; create 400 |
| Repeat approval, premature fulfillment, or old-snapshot action | 400 |

Use disposable records for direct-delete checks. After denied mutations, reread attempted fields. For actor-configuration checks, change one fixture at a time, restore it immediately, and verify GET `/model` returns 200 again. A generic 400 alone does not prove which guard fired.

## Finish

Restore the original three active actors, their demo roles, fixed policy, and administrator browser context. Keep the completed records as evidence. Do not expose the vulnerable policy outside the synthetic demonstration.

Local verification against the actual vulnerable export found a violation at shortest depth 2 within bound 3; replay matched its live result. The corrected export had no violation within bound 3. This is a sequential sample with no concurrency guarantee, real provisioning, or proof of arbitrary ServiceNow behavior.

See PDI_LIVE_STATUS.md for the actual observations and limitations. Repeating the demo creates new evidence; never relabel saved results as a new run.
