# Validation and access boundary

This is the initial November 13 local record. Later [live PDI validation](PDI_LIVE_STATUS.md) and [workspace 0.2 validation](WORKSPACE_VALIDATION.md) are separate reports. Historical statements below apply to that initial checkpoint.

Executed locally on November 13, 2026. Environment: macOS arm64, Python 3.13.11, Node.js 24.14.1, FastAPI 0.162.5, Z3 5.4.1 (Python package `z3-solver` 5.4.1.0). Exact dependency versions are in `requirements.lock`.

| Check | Observed outcome |
|---|---|
| `python -m pytest -q` | 34 passed; one upstream Starlette TestClient deprecation warning about its httpx transport |
| Vulnerable model at bound 3 | Violation found at shortest depth 2: Alice submits, Alice approves |
| Concrete evidence replay | Reproduced the final self-approved state |
| Fixed model at bound 3 | No violation within bound |
| Exhaustive small-model comparison | Z3 and concrete exploration agreed on 50 eligibility/policy configurations |
| JavaScript/Python parity | Actual supplied `GenesisCore.js` agreed with Python over the tested assignments, states and actions |
| Real Uvicorn HTTP smoke check | `/health`, `/docs`, `/openapi.json`, verification, replay and unsupported-feature result passed |
| Dependency consistency | `pip check`: no broken requirements |
| ServiceNow gateway/resource JavaScript syntax | Node syntax checks passed |

The first virtual environment later stalled while reading some package files. A fresh environment in a temporary runtime directory, installed from the exact version pins, successfully started the server and passed the HTTP checks. The cause of the file-read stall was not established. This is not evidence of a workflow or solver defect.

The local API was left running at `http://127.0.0.1:8000` after validation; its lifetime depends on this desktop session. The portable startup command is in the README. The API has no credentials and does not write to ServiceNow.

## Supplied evidence

- `evidence/vulnerable.json`: deterministic, hashed synthetic counterexample.
- `evidence/fixed.json`: bounded result for the corrected policy.
- `evidence/replay.json`: concrete reproduction of the counterexample.
- `evidence/model.json`: supported transition representation.
- `evidence/pytest.xml`: test report from the fresh pinned environment.
- `evidence/http-smoke.json`: observed real local HTTP results.

## Not executed or established

No ServiceNow instance URL, credentials, or connected instance was supplied. Therefore no live PDI installation, live export, ServiceNow REST action, ACL enforcement test, ATF run, or actual provisioning was performed. The installer is a manual, reviewable procedure with scripts, not a claimed deployed application. Node tests do not substitute for a real PDI runtime.

The GitHub Actions workflow was prepared but not run on hosted infrastructure. No production repository, deployment, release gate, or external application was modified. No enterprise-scale performance, outage reduction, comparative detection advantage, or research novelty beyond the implementation was established.

The live acceptance steps are in `docs/PDI_SETUP.md`. Completing them requires the user's PDI and authorized account access. These steps are the next dependency before presenting the project as a validated live ServiceNow integration.
