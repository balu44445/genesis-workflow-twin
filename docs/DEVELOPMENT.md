# Developer guide

Workspace 0.2 adds [the local dashboard and installation tools](WORKSPACE_0_2.md). See [current local validation](WORKSPACE_VALIDATION.md) and the separate [live PDI record](PDI_LIVE_STATUS.md). The initial development notes below predate those live tests.

## Layout

| File/directory | Responsibility |
|---|---|
| `genesis/model.py` | Strict contract validation, supported-subset check, lowering, canonical SHA-256 |
| `genesis/verifier.py` | Z3 bounded reachability and deterministic shortest witnesses |
| `genesis/replay.py` | Concrete state transition interpreter and evidence replay |
| `genesis/api.py` | FastAPI `/health`, `/model`, `/verify`, `/replay` |
| `genesis/runtime.py` | Transactional local requests, optimistic versions, durable evidence timeline |
| `genesis/explain.py` | Local summaries and opt-in anonymous AI adapter |
| `genesis/install.py` | Target actor mapping and offline installation plan/export comparison |
| `genesis/static/` | Same-origin dashboard assets and bundled fixtures |
| `servicenow/GenesisGuard.js` | Permanent unique stage claims; uninstalled source candidate |
| `genesis/extract.py` | GET-only ServiceNow contract adapter |
| `genesis/cli.py` | Source-checkout demo, model, verify, replay, extract commands |
| `servicenow/GenesisCore.js` | Actual PDI transition implementation, exercised locally under Node |
| `servicenow/GenesisGateway.js` | Identity, role/active-user checks, fixed table persistence |
| `servicenow/resource_*.js` | Authenticated Scripted REST handlers |
| `tests/` | Verification, replay, parity, API, extraction, concurrency and boundary tests |

Use the repository from its extracted source directory for the supplied demo; example fixtures and docs live beside the package. `pip install -e '.[dev]'` is an alternative for local development. The checked-in exact version pins reproduce this run; they are not a supply-chain hash lock or an assurance of future dependency compatibility.

## Test design

The tests check observable properties and independent implementations:

1. Vulnerable input must yield a two-step counterexample, and every generated event must replay.
2. The corrected guard must reject self-approval while still allowing Alice→Bob approval and Carol fulfillment.
3. Fifty valid two-user eligibility/policy configurations are exhaustively explored with a concrete interpreter and compared with Z3's verdicts.
4. The **same JavaScript file supplied for ServiceNow** runs in a Node VM and is compared against Python over reachable states, initial assignments, valid/invalid actions, and unknown actors. Only `Class.create` is shimmed; no ServiceNow data or API is fabricated as a live result.
5. Unknown semantics/features return inconclusive; malformed, duplicate, missing-role, and over-limit inputs fail validation.
6. Tampered evidence and changed snapshot hashes fail replay.
7. Forced solver unknown yields inconclusive; independent Z3 contexts support concurrent verification calls.
8. FastAPI is exercised end to end in process. Extraction is tested with a mock HTTP transport for wrapped/unwrapped exports, read-only behavior, authentication headers, URL boundaries, size limits, and HTTP failures.
9. CLI verification returns the intended release-check exit codes.

Local Python/JavaScript parity does not establish ServiceNow runtime fidelity. Follow the live acceptance steps separately and record the actual instance release. No ATF suite execution, live REST calls, ACL validation, or production deployment has occurred.

## API example

```python
import json
from pathlib import Path
import httpx

snapshot = json.loads(Path('examples/vulnerable.json').read_text())
response = httpx.post('http://127.0.0.1:8000/verify', json={
    'snapshot': snapshot, 'bound': 3, 'timeout_ms': 2000,
})
response.raise_for_status()
evidence = response.json()
assert evidence['status'] == 'violation'
```

Statuses are domain results, so both findings and inconclusive verification return HTTP 200. Malformed inputs return 422. A caller must inspect `status`, `bound`, and `scope`; HTTP success alone does not mean the workflow satisfies the invariant.

## Extending the supported subset

Change the semantic version when introducing behavior. Define state, transition guards, effects, frame conditions, and an invariant before extending the solver. Update the PDI core, Python interpreter, Z3 encoding, and lowering together. Add a deliberately vulnerable fixture and a fixed fixture, exhaustive small-model comparison, and JavaScript parity cases for the new behavior. Validate on a real PDI before removing its unsupported marker.

Do not silently interpret unknown JavaScript as a no-op. Do not reuse a bounded UNSAT result as an unbounded proof. Delegation requires modeling the relation between human and account identity; adding another user to a role list does not model control of that identity.

## CI

The supplied GitHub Actions workflow runs tests, the paired demo, and the fixed-model check without credentials. It has not been executed on hosted GitHub Actions. It assumes this directory is the repository root. It is a project validation example, not an attached production release gate. A real gate must require an approved export source, expected semantic version, adequate bound, no unsupported features, and validated runtime fidelity in addition to a zero CLI exit status.

## Troubleshooting

- No Z3 wheel for your environment: use a supported CPython/OS combination; this run used macOS arm64 and Python 3.13.
- Parity test reports Node missing: install Node.js 20+ and rerun. Do not silently skip the test.
- Export returns 401/403: check authentication, API/resource ACLs and `u_genesis_demo` role.
- Export returns 400: confirm the manifest schema, actual actor sys_ids, active flags and explicit sample role assignments.
- PDI actions return 400 after editing configuration: create a new sample request; the stored snapshot is intentionally immutable.
- Verification inconclusive: inspect declared unsupported features and the time budget; do not label the result safe.
