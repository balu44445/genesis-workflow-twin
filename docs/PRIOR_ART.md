# Prior art and positioning

Research checked on November 13, 2026. This is a focused literature/product check, not an exhaustive novelty search or patent assessment.

| Existing work | What it establishes | Implication for GENESIS |
|---|---|---|
| [Digital Twins of Business Processes: A Research Manifesto](https://arxiv.org/abs/2410.08219), submitted September 2024 | Business-process digital twins are an established research topic, with real-time representation and research challenges | Do not claim to invent workflow digital twins |
| [Formal Verification of Business Constraints in Workflow-Based Applications](https://www.mdpi.com/2078-2489/15/12/778), 2024 | Formal checking of business constraints in workflow applications predates this project | Neither formal workflow verification nor its combination with business constraints is new |
| [A Survey on Workflow Satisfiability, Resiliency, and Related Problems](https://arxiv.org/abs/1706.07205), 2017 | Authorization and separation-of-duty constraints have a substantial workflow research history | Do not claim the self-approval constraint or user-assignment search is a new algorithm |
| [ServiceNow: What is process mining?](https://www.servicenow.com/workflows/creator-workflows/what-is-process-mining.html) | ServiceNow explicitly describes process discovery from event data as producing a digital twin and discusses conformance checking | Do not position GENESIS as the first ServiceNow process twin |
| [ServiceNow Automated Test Framework: REST test steps](https://www.servicenow.com/docs/r/application-development/automated-test-framework-atf/rest-test-steps.html) | Existing platform tests can exercise REST behavior | Use ATF to validate concrete runtime scenarios; do not claim ATF cannot find the seeded defect |
| [ServiceNow Instance Scan](https://www.servicenow.com/docs/r/platform-administration/instance-scan/hs-landing-page.html) | Existing configuration checks identify health and best-practice issues | Benchmark against an explicit custom check as well as generic test cases |

## Defensible claim

“GENESIS is a ServiceNow-focused proof of concept that exports a controlled approval contract, checks an explicit segregation-of-duties invariant with Z3, and emits a hashed, reproducible counterexample.”

The potentially useful contribution is integration quality: a clear semantic boundary, runtime/model parity, reproducible evidence, and a practical PDI demonstration. Originality beyond this implementation has not been established. A snapshot-only MVP is a step toward a digital twin, not a continuously synchronized enterprise twin.

## Proposed comparison, not achieved results

Run the same seeded configurations against ordinary happy-path tests, a targeted self-approval REST/ATF test, a purpose-built Instance Scan check, and GENESIS. Record detection, false positives, unsupported cases, authoring effort, and elapsed verification time. A targeted conventional test can find this simple defect. GENESIS's intended benefit is systematic exploration over the modeled user/assignment combinations and reusable counterexample generation, not an unsupported claim of superiority.

Sources for implementation: [ServiceNow scripted REST resources](https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/t_CreateAScriptedRESTAPIResource.html), [GlideRecord reference](https://www.servicenow.com/docs/r/api-reference/server-api-reference/c_GlideRecordAPI.html), [Z3 Python reference](https://z3prover.github.io/api/html/z3.z3.html), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/).
