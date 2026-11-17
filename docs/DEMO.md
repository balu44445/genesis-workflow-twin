# Five-minute demonstration

## Accurate opening

“GENESIS is a proof of concept for verifying a controlled ServiceNow approval workflow. It checks possible user assignments against an explicit separation-of-duties policy and produces a replayable failure. Business-process twins and formal workflow verification have prior art; this project explores a practical ServiceNow integration.”

## Local demonstration

1. Show `examples/vulnerable.json`: Alice is a requester and an eligible approver; Bob is another approver; Carol fulfills. Distinct approval is disabled.
2. Run `python -m genesis.cli demo`. Show `evidence/vulnerable.json` and its two-step trace: Alice submits and Alice approves her own request. Explain that this is a synthetic finding computed by the implementation, not an observed production incident.
3. Run `python -m genesis.cli replay examples/vulnerable.json evidence/vulnerable.json`. Show `reproduced: true` and the final state.
4. Show `examples/fixed.json`: distinct approval is enabled. Run `python -m genesis.cli verify examples/fixed.json --bound 3`. Explain the exact bounded result and model assumptions.
5. Show the test result, especially exhaustive small-model comparison and JavaScript parity. A happy-path Alice→Bob test passes in both variants; a targeted self-approval test could also find this defect. Do not claim conventional tools cannot detect it.

Use `.venv/bin/python` where the virtual environment is not activated.

## Live PDI extension

Only after installation and actual runtime validation: export from the PDI, verify the live snapshot, and execute the trace as Alice via authenticated sample endpoints. Show the same PDI request blocked under the corrected policy using a new record, followed by a valid Alice→Bob→Carol completion. Record actual outcomes. Never substitute a Node mock for evidence of a live PDI run.

## What the project demonstrates

Inspectable workflow modeling, ServiceNow server-side scripting and REST design, finite-state verification with Z3, reproducible evidence, and tests comparing independent semantics. There is no measured claim about outage reduction, executive approval, real-world detection rates, or production scale.

## Next useful milestone

Validate the supplied sample on a real PDI, record runtime/model discrepancies, then add one carefully defined behavior such as rejection. Broader Flow Designer extraction should come only after a versioned semantic contract and real-instance parity tests exist for each supported action.
