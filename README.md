# GENESIS — workflow twin and verification MVP

**Workspace 0.2:** open the [dashboard guide](docs/WORKSPACE_0_2.md) for the request simulator, evidence timeline, policy previews and optional AI connection. New ServiceNow concurrency code is a [source candidate](docs/CONCURRENCY_UPGRADE.md), separately labeled from the previously live-validated PDI export.

GENESIS checks a small approval workflow for **requester self-approval**, returns the shortest reproducible counterexample, and verifies a corrected configuration within an explicit bound. It contains a Python/FastAPI service, Z3 bounded model checker, concrete replay interpreter, and a ServiceNow PDI sample with matching JavaScript semantics.

This is a snapshot-based workflow twin prototype. It is **not the world's first workflow digital twin**, a complete ServiceNow emulator, or a production safety certificate. See [prior art](docs/PRIOR_ART.md).

## Run locally

Requires Python 3.11+ and Node.js 20+ (Node is used by the semantic parity test). From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m genesis.cli demo
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn genesis.api:app --host 127.0.0.1 --port 8000
```

Open the [dashboard](http://127.0.0.1:8000/) or [API explorer](http://127.0.0.1:8000/docs). The service runs locally without ServiceNow credentials. The local API has no authentication; keep the supplied loopback binding. You can copy the contents of `examples/vulnerable.json` into the `/verify` request's `snapshot` field. External AI stays disabled unless explicitly configured and selected; local explanations send no data externally.

## Public portfolio demo

The internet-facing package is deliberately narrower than the local API. It accepts only the bundled synthetic actors and workflow, isolates temporary visitor data, disables external AI and ServiceNow connections, requires HTTPS, and limits bodies, solver depth/time, concurrency, sessions, writes and storage. Use `genesis.public:public_app` (via `python -m genesis.serve`), never the unauthenticated local entry point. A Docker image and Render Blueprint are included; see the [public deployment guide](docs/PUBLIC_DEMO.md). They are prepared and locally tested, but no public deployment or domain is claimed.

The demo produces:

| Input | Expected result | Meaning |
|---|---|---|
| `examples/vulnerable.json` | `violation` | Alice submits, then approves her own request in two transitions |
| `examples/fixed.json` | `no_violation_within_bound` | The distinct-approver guard prevents this violation at depths 0–3 |
| Unsupported semantics/features | `inconclusive` | No safety conclusion is available |

The shortest witness ends at approval because the invariant already fails there. Fulfillment is also modeled and exercised in tests.

```sh
.venv/bin/python -m genesis.cli verify examples/vulnerable.json --out evidence/vulnerable.json
# The preceding command intentionally exits 2 because it found a violation.
.venv/bin/python -m genesis.cli replay examples/vulnerable.json evidence/vulnerable.json
.venv/bin/python -m genesis.cli verify examples/fixed.json --bound 3
.venv/bin/python -m genesis.cli model examples/vulnerable.json
```

Exit codes: `0` = no violation within bound or successful utility command; `2` = violation; `3` = inconclusive; `1` = invalid input/operation. A short bound can miss a violation. Never interpret exit `0` alone as a platform-wide safety claim. The `demo` command exits `0` only when it obtains both expected demonstration results.

## Connect a PDI

Follow [PDI setup](docs/PDI_SETUP.md) and the [concurrency upgrade prerequisites](docs/CONCURRENCY_UPGRADE.md) to create the sample tables, roles, properties, Script Includes, and authenticated REST resources. The earlier sequential version was [live-validated on a private development PDI](docs/PDI_LIVE_STATUS.md). The current gateway/guard upgrade has local interleaving tests only and is not installed there. Local tests do not validate live database uniqueness, GlideRecord behavior, or target-instance ACL enforcement.

After installation, configure `SN_EXPORT_URL` to the actual GET resource URL shown by your instance and authenticate using either `SN_TOKEN` or `SN_USERNAME` + `SN_PASSWORD`. Keep credentials in your environment; do not put them in source files or evidence. See the setup guide for a password prompt example.

```sh
.venv/bin/python -m genesis.cli extract --out live-snapshot.json
.venv/bin/python -m genesis.cli verify live-snapshot.json --out live-evidence.json
```

Extraction is GET-only, TLS-verified, and does not follow redirects. It reads the sample's explicit contract, **not arbitrary Flow Designer or legacy workflow metadata**. Simulation/replay is local and never writes back to ServiceNow. Reproducing a witness in the PDI requires explicitly executing the sample POST requests as the indicated users.

## Documentation and evidence

- [Architecture and supported semantics](docs/ARCHITECTURE.md)
- [Prior art and defensible positioning](docs/PRIOR_ART.md)
- [PDI installation and live acceptance steps](docs/PDI_SETUP.md)
- [Developer guide and test design](docs/DEVELOPMENT.md)
- [Five-minute demonstration](docs/DEMO.md)
- [Public demo deployment and boundaries](docs/PUBLIC_DEMO.md)
- [Validation record and access boundary](docs/VALIDATION.md)
- `evidence/`: reproducible synthetic findings and replay results; no live PDI data.

No target JD or verified personal work history was supplied. The files demonstrate project work in Python, REST, ServiceNow scripting, formal modeling, and testing; they do not establish employment history or years of experience.
