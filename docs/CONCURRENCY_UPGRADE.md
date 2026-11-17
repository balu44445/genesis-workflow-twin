# ServiceNow concurrency upgrade — source candidate

Status: implemented and tested locally with controlled storage interleavings. **Not installed or concurrency-tested on a live PDI.** The old exported XML remains the previously validated sequential version.

## Design and boundary

The three-stage workflow advances monotonically. Before writing an action, GenesisGateway computes its allowed next state, then GenesisGuard inserts an immutable stage claim whose key is `<request sys_id>:<before state>`. A database UNIQUE constraint permits one claim for that request/stage. The winner rereads the request, checks its snapshot/state, and writes the result. Invalid actions are rejected before consuming a claim. Later stages use different keys.

Claims are retained permanently. A failed or uncertain write blocks that stage until administrator review. There is no expiring lock, automatic claim deletion, or assumption that a timeout rolled back the state. This deliberately trades automatic recovery for a fail-closed boundary. It relies on the target database's real uniqueness enforcement and on all non-admin writes going through this gateway. Direct administrator changes, configuration races, external automation and new workflow shapes remain outside this guarantee.

The state and claim are separate records, so a response error can follow an applied state change if claim completion fails. Reread the request and claim after any uncertain error. Do not blindly retry an action. The existing generic resource 400 remains compatible but cannot distinguish rejection from an uncertain write; the claim ledger and persisted request are authoritative for recovery.

## Install in a development instance

1. Retain a backup and create a **new** upgrade update set. Do not relabel the earlier export as containing this change.
2. Create standalone `u_genesis_action_claim`. Table read/create/write/delete and field mutation must require admin. The privileged gateway uses it after explicit authorization. Keep direct non-admin access denied.
3. Add fields:

| Field | Type | Requirement |
|---|---|---|
| u_key | String 80 | Mandatory, **Unique**; actual database uniqueness must be verified |
| u_request | Reference u_genesis_request | Mandatory |
| u_actor | Reference sys_user | Mandatory |
| u_action | String 20 | Mandatory |
| u_before | String 4000 | Mandatory |
| u_after | String 4000 | Mandatory |
| u_outcome | String 20 | claimed/applied |

4. Verify `sys_dictionary` marks u_key unique, inspect its database index, and in a disposable fixture prove duplicate insertion is rejected. The runtime metadata check alone does not prove physical uniqueness.
5. Install active Global, scope-only, server-side GenesisGuard.js, with client/mobile callable disabled. Install the updated GenesisGateway.js only after the table/index and guard are ready. GenesisCore and REST resource scripts are unchanged.
6. Verify no unrelated business rule, workflow or integration mutates these tables. Restore all original actor roles and fixed policy before testing.
7. Run concurrent requests using separate authenticated sessions: two approvals of the same pending request must yield one state advance and one stage claim. Reread state, approved-by and claims. Then fulfill once. Test failure/uncertainty recovery in a disposable instance; do not claim live concurrency safety from the local mock.
8. Repeat authentication/ACL tests, remove temporary elevation, export the upgrade set, and audit all customer updates before distribution.

Official basis: [ServiceNow Brazil: require unique values](https://www.servicenow.com/docs/r/platform-administration/t_RequiringUniqueValuesForAField.html) documents the uniqueness constraint and index considerations. The claim protocol above is this project's design, not a vendor-provided transaction API.

## Recovery procedure

Suspend writes to the affected request and confirm no worker is still executing. Compare claim before/after values, actor/action and snapshot against the persisted request. If state matches the intended result, record completion without replaying the action. If state matches the original, confirm the earlier operation has stopped before an administrator authorizes any targeted repair. If neither matches, keep writes blocked and investigate. Never routinely delete claims or restore a whole database to clear one failure. Retain recovery evidence.
