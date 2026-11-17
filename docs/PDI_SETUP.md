# Install and reproduce on a ServiceNow PDI

Status: the earlier sequential sample was installed and [live-validated](PDI_LIVE_STATUS.md). Current source adds an uninstalled concurrency upgrade: **follow [CONCURRENCY_UPGRADE.md](CONCURRENCY_UPGRADE.md) to create the claim table/unique key and install GenesisGuard before the current GenesisGateway**. Current local tests do not establish live host/database behavior. UI labels can vary by release. Use a disposable PDI with synthetic users and no real access provisioning.

## 1. Prerequisites and scope

- An active Personal Developer Instance and admin access to configure it.
- `web_service_admin` for Scripted REST resources; elevate to `security_admin` when editing ACLs if required by the instance.
- Work in **Global** for this MVP so the supplied `u_` table, role, property, and Script Include names match. Do not paste unchanged into a scoped application. A scoped version would need consistent namespace/table/role replacements and cross-scope testing.
- No Process Mining, IntegrationHub, Now Assist, or paid AI plugin is required by these scripts.

Keep the sample in its own update set using your PDI's normal configuration tools. A separately audited [downloaded XML package](PDI_PACKAGE_INSTALL.md) exists for the earlier live-validated sequential version; it does not contain the current concurrency upgrade. No XML metadata was invented for the upgrade.

## 2. Table, role, and synthetic users

Create a standalone custom table named **GENESIS Request** with technical name **`u_genesis_request`**, without extending Task. Add these fields with these exact technical names:

| Field | Type | Length/reference |
|---|---|---|
| `u_state` | String | 20 |
| `u_requester` | Reference | `sys_user` |
| `u_assigned_approver` | Reference | `sys_user` |
| `u_approved_by` | Reference | `sys_user`, initially empty |
| `u_snapshot` | String | 4000 |

Enable auditing for the sample table/fields if you want a visible record history. Do not attach other Flows, Business Rules, notifications with state changes, or provisioning integrations.

Create role **`u_genesis_demo`** and three active, non-admin synthetic users: Alice, Bob, Carol. Assign this role explicitly to each and copy each `sys_user.sys_id`. Do not use the built-in admin as Alice: the sample authorizes transitions by actual user ID. Configured eligibility in the manifest is independent of the platform role, which only permits access to the sample API.

If you will use REST API Explorer for the demonstration, also assign **`rest_api_explorer`** to each synthetic user. This is required to open Explorer as that user; `u_genesis_demo` alone does not grant Explorer access. You can instead use an external REST client authenticated separately as Alice, Bob, or Carol, with only the sample role. See the official [Explorer access requirements](https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/t_GetStartedAccessExplorer.html). Do not grant admin or web_service_admin to the test actors just to access Explorer.

Protect direct record mutation: set the table's create/write/delete ACLs and corresponding field write ACLs to **admin only**. Give `u_genesis_demo` read access to this synthetic table and its fields. Review auto-generated ACLs to avoid accidentally retaining broader direct writes. Keep the Script Includes server-side and not client callable. `GenesisGateway` intentionally uses privileged `GlideRecord` after its own role/identity checks, so the API can persist only the allowed transitions while ordinary table/form writes are blocked. This is a sample gateway pattern, not a general ACL verification claim.

Verify as Alice that direct form/Table API changes to state and approved_by are denied. Administrators remain capable of bypassing the sample. Do not treat an admin-modified record as evidence of modeled behavior.

## 3. Configuration property and Script Includes

Create a String system property **`u_genesis.manifest`**. Paste `examples/vulnerable.json` into its value, replace actor IDs `alice`, `bob`, and `carol` with their actual 32-character sys_ids, and set source to:

```json
{"kind":"servicenow_export","description":"GENESIS PDI sample configuration"}
```

Keep `schema_version`, `semantics`, `steps`, and the role lists unchanged. Only administrators should be able to edit this property. The gateway normalizes the source field on export. Ensure the stored request snapshot will fit the 4000-character field; the three-user example is much smaller.

Create two active, Global, server-side Script Includes named exactly **GenesisCore** and **GenesisGateway**. Paste the corresponding `.js` files from `servicenow/`. Client callable: **false**. Their prototype `type` names already match.

Review the deployed code against these files before trusting the exported contract. The export declares a semantic version; it does not remotely attest that the deployed code matches it.

## 4. Authenticated Scripted REST API

Create a Scripted REST API called GENESIS, API ID `genesis`. Use the **actual Base API path** displayed by your instance; do not assume the namespace is `global`. Require authentication. Add a REST endpoint ACL of type `REST_Endpoint` requiring `u_genesis_demo`, and associate it with the API/resources under the security settings. Leave authentication and ACL authorization enabled on every resource. The server-side gateway also checks this role.

Create these resources:

| Method | Relative path | Script |
|---|---|---|
| GET | `/model` | `servicenow/resource_get_model.js` |
| POST | `/requests` | `servicenow/resource_create_request.js` |
| POST | `/requests/{id}/actions` | `servicenow/resource_action.js` |

Accept and return `application/json`. Anonymous calls must be denied. Role-free users must be denied. Role names and REST ACL configuration should be checked in REST API Explorer on your PDI. Official [resource creation instructions](https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/t_CreateAScriptedRESTAPIResource.html) describe the platform setup and required role.

## 5. Read-only extraction from Python

Use an authorized export account with `u_genesis_demo`, or an appropriately authorized admin. The gateway checks that every configured actor exists, is active, and has the sample role. The adapter supports a bearer token or basic authentication; your instance must permit the selected method. A token is not created by this project.

Example in zsh, from the repository directory (replace the URL and username):

```sh
export SN_EXPORT_URL='https://YOUR-PDI.service-now.com/api/YOUR-NAMESPACE/genesis/model'
export SN_USERNAME='YOUR-EXPORT-USER'
read -s 'SN_PASSWORD?PDI password: '
export SN_PASSWORD
.venv/bin/python -m genesis.cli extract --out live-snapshot.json
.venv/bin/python -m genesis.cli verify live-snapshot.json --out live-evidence.json
unset SN_PASSWORD
```

For bearer authentication, set `SN_TOKEN` instead and unset `SN_USERNAME`/`SN_PASSWORD`. Credentials never appear in generated evidence. Actor names and sys_ids do, so keep live exports local. Do not add live exports to source control. Basic auth availability, OAuth setup, instance wake-up, credentials, and certificate/network reachability depend on your environment.

## 6. Reproduce the counterexample on the PDI

Use REST API Explorer with the session **impersonating the exact synthetic actor**. Ensure the authenticated user is Alice for steps 1–3. Do not send `actor` or `requester` fields: the gateway derives identity from the authenticated session.

1. With vulnerable policy `require_distinct_approver: false`, POST `/requests` with `{"assigned_approver":"ALICE_SYS_ID"}`. Expect 201 and `runtime.state=draft`; save the returned request sys_id.
2. POST `/requests/REQUEST_SYS_ID/actions` with `{"action":"submit"}`. Expect pending.
3. As Alice, POST the same action endpoint with `{"action":"approve"}`. Expect approved, with `runtime.approved_by == runtime.requester`. This is the concrete PDI violation predicted by the model.
4. Optionally impersonate Carol and send `{"action":"fulfill"}`. Expect fulfilled with the violating approved_by preserved. This remains synthetic; it provisions nothing.
5. As admin, set `require_distinct_approver: true` and change `revision` to `demo-fixed-1`. Extract again and verify. Expect no violation within bound 3.
6. Create a **new** Alice→Alice request and submit. Alice's approve action must now return 400 and the record must remain pending. Existing records reject all subsequent actions after a configuration change, by design.
7. Show a valid completion: Alice creates a new request assigned to Bob and submits; Bob approves; Carol fulfills. Expect fulfilled and approved_by=Bob.

Minimum live acceptance checks also include unknown actor/role denial, fulfill-before-approve denial, repeated approve denial, anonymous and role-free requests denied, direct table mutation denied, and a missing/inactive configured user causing export rejection.

These steps are **pending user-instance validation**. Record your ServiceNow release/build, exact resource URLs, response codes, returned states, and audited changes after execution. Do not mark them passed based only on the local Node tests.

## 7. Limitations and cleanup

The persistence gateway is designed for a single-user-at-a-time demonstration. It does not provide an atomic compare-and-swap across concurrent updates. Concurrency, admin bypass, other table logic, direct writes, and configuration changes during a request are outside the verified model. A PDI result demonstrates fidelity only for the exercised setup.

To clean up, deactivate the sample REST API and Script Includes, remove the manifest property and test records, and remove synthetic users/role/table using normal PDI administration after checking dependencies. No automatic deletion or production deployment is performed.
