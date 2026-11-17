# GENESIS workspace 0.2

This local release adds a dashboard, transactional request simulator, decision timeline, policy comparison, target-installation preparation, and optional AI explanations. The previously exported ServiceNow update set is a separate **0.1 live-validated artifact**. Its results do not validate the new gateway guard.

## Start

Install requirements as in README.md, then run:

```sh
python -m uvicorn genesis.api:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765. Keep the loopback binding: the simulator has no authentication and uses explicitly selected synthetic identities. It does not impersonate a ServiceNow user or write to a PDI. The browser rejects cross-origin mutations, uses same-origin scripts/styles, and renders evidence as text.

Requests, immutable snapshots, versions, accepted events and rejected attempts are saved in SQLite at `pdi-local/dashboard.sqlite3`. Set `GENESIS_DB` to another private path to start an isolated workspace. Event/state writes use one transaction. `BEGIN IMMEDIATE` serializes competing writers; a stale expected version returns 409 without changing state. Use this on a local filesystem, not a network-shared database file.

## Demonstrate

1. Choose the vulnerable fixture; run verification at depth 3. Inspect the two-step violation and its concrete replay.
2. Select the distinct-approver proposal; preview the change. Compare current/proposed results without applying anything.
3. Load the corrected fixture. Create an Alice → Bob request, submit as Alice, approve as Bob, and fulfill as Carol. Follow accepted events in the timeline.
4. Create an Alice → Alice request under the corrected policy. Submit, then approve as Alice. The rejection reason and unchanged state appear in the timeline.
5. Download a selected request's evidence. It is labeled `synthetic_simulation`, not live PDI evidence.

Every result shows a fingerprint, bound and sequential scope. Imported JSON's source label is a claim to inspect, not independently authenticated provenance. Delegation, amount thresholds, multiple approval stages and arbitrary scripts are visibly unsupported. Extending these requires new semantics, tests and model parity; unsupported inputs remain inconclusive.

## AI boundary

Local explanations are deterministic summaries of newly computed verifier evidence. They are explicitly labeled **no external AI**. The external adapter is implemented but remains off by default and has only been tested with a mock provider.

To enable it later, obtain approval for the destination/data and configure credentials privately on the server:

- `GENESIS_AI_ENABLED=true`
- `OPENAI_API_KEY` via a private environment or secret manager
- `GENESIS_AI_MODEL` as an explicitly chosen, available model

The browser never receives the key. Each external call also requires selecting the external-AI checkbox. The adapter calls only the official HTTPS Responses endpoint, follows no redirects, disables response storage, and sends derived status, bound, property and sequential scope. It omits names, actor IDs, snapshots, source descriptions and request histories. Provider explanations are reviewable drafts and cannot change policy or execute actions. Storage settings do not replace reviewing the provider's data handling requirements.

Reference: [official OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create). No real provider request was performed for this release.

## Prepare a second PDI

```sh
python -m genesis.cli prepare-pdi --alice <32-character-target-id> --bob <32-character-target-id> --carol <32-character-target-id> --out-dir pdi-local/target-plan
```

This validates distinct IDs and writes a corrected `manifest.json` plus `installation-plan.json`; it performs no live calls or user/role grants. Follow PDI_PACKAGE_INSTALL.md for the existing transport, then CONCURRENCY_UPGRADE.md for the new guard. After authenticated read-only extraction to a private file:

```sh
python -m genesis.cli check-install pdi-local/target-export.json pdi-local/target-plan/manifest.json
```

This compares model exports only. It does not validate live ACLs, database uniqueness, or concurrent behavior. A second instance URL has not been supplied; clean target installation remains pending.
