# GENESIS public prior-art evidence

Search date: November 17, 2026. Sources: publicly indexed GitHub repositories, public LinkedIn posts, publisher pages, project websites and vendor documentation. These sources were read; third-party projects were not installed or executed. Comparisons below are assessments of documented scope, not benchmarks or proof of implementation quality.

## Finding

The general idea is established: workflow model checking, separation-of-duty constraint solving, counterexample traces, policy comparison and AI-assisted workflow verification all have public precedents. This search did not establish an identical public implementation of the entire current GENESIS ServiceNow/Z3/replay/demo bundle. That absence does not establish uniqueness; private, unindexed or differently named work may exist.

## Close research and implementation evidence

### 1. Oracle APEX workflow verification with generative AI — closest combined example

Florin Stoica and Laura Florentina Stoica, *Formal Verification of Business Constraints in Workflow-Based Applications*, Information 15(12), 778, published December 5, 2024.

- Paper: https://www.mdpi.com/2078-2489/15/12/778
- Implementation repository: https://github.com/workflow-atl/ATL
- Public LinkedIn post discussing the paper: https://www.linkedin.com/posts/information-mdpi-a0551a110_newpaper-workflow-formalverification-activity-7285297733005983744-I3_l

Evidence locations: paper sections 3.3, 5, 6 and Data Availability Statement; repository README. The authors describe extracting Oracle APEX workflow structure, translating it into a concurrent game structure, checking ATL properties, and experimenting with a GPT-4o assistant that translates informal constraints into formal formulas. The repository lists Java model-checker code, SQL setup/extraction scripts, JSON examples and XML schemas. The publisher provides the publication date. Amanda Liu's LinkedIn post publicizes the authors' work; it is not an independent validation of the implementation.

Overlap: workflow models + formal verification + business constraints + AI support + platform integration. Difference: Oracle APEX/ATL; GENESIS uses a narrow explicit ServiceNow contract/Z3 and currently prepares AI explanations rather than formal-property translation. The paper describes graphical violation-sequence feedback as future work, so it must not be presented as already implemented there. This is strong evidence against a broad claim that AI-assisted formal workflow verification is new.

### 2. Workflow Satisfiability Problem solver

- Repository: https://github.com/salmanmkc/Workflow-Satisfiability-Problem
- Listed implementation file: workflowSatisfiabilityProblem.py.

The README describes a Python/Google OR-Tools constraint solver supporting authorization, binding of duty, separation of duty, at-most-k and team constraints, with instance folders and a tester. The author's December 2021/January 2022 description is self-reported and was not independently dated through commit history. The raw implementation file could not be retrieved through the research browser; claims here rely on the readable repository README/file listing.

Overlap: programmatic workflow authorization and separation-of-duty analysis. Difference: finding an assignment that satisfies constraints is not the same problem as finding an allowed execution that violates a policy invariant. No ServiceNow integration was established from this source.

### 3. BPMN Analyzer 2.0

- Browser modeler: https://github.com/timKraeuter/bpmn-analyzer-js
- Model checker: https://github.com/timKraeuter/rust_bpmn_analyzer
- 2024 paper: https://arxiv.org/abs/2408.06028

The repositories document model checking, BPMN control-flow analysis, error visualization and possible quick fixes. The modeler's README describes a counterexample token flow and browser-side WebAssembly deployment; the Rust checker documents deadlocks/livelocks and control-flow properties.

Overlap: workflow model checking + visual counterexamples + browser interface + correction support. Difference: its documented focus is BPMN control-flow correctness, not GENESIS's particular requester-self-approval invariant or ServiceNow adapter.

### 4. SCV compliance-verification framework

- Repository: https://github.com/davidknuplesch/SCV

The README's `verifyLocalCompliance` documentation describes compliance checking and counterexamples. Its worked example reports a violating trace `acbd`. It also supports checking decompositions of compliance rules. The repository calls itself a proof-of-concept.

Overlap: process model + rule + reproducible violating trace. Difference: a different process/rule representation; no equivalent ServiceNow integration was established.

### 5. VBPMN

- Project site: https://pascalpoizat.github.io/vbpmn-web/

The project website documents formal BPMN model comparison, intermediate-model translation, counterexamples, a web interface, REST integration, and LOTOS NT/CADP verification.

Overlap: model comparison + formal analysis + counterexample feedback + web/REST interface. Difference: behavioral comparison of BPMN processes rather than the current GENESIS approval contract.

## LinkedIn evidence and its limits

In addition to the paper announcement above, Yasser Saber publicly describes a ServiceNow-connected digital-twin prototype using Google 3D Tiles/CesiumJS to detect operational issues and create incidents/maintenance actions:

https://www.linkedin.com/posts/yassersaber_servicenow-digitaltwin-smartcity-activity-7496125154620710912-CxuQ

This supports an overlap in digital-twin/ServiceNow integration at the level of the author's public demonstration claim. The inspected post does not establish formal checking of approval invariants, a Z3 implementation, source availability, production adoption or independent test results. It is adjacent work, not an identical project. Relative LinkedIn timestamps were not converted into unsupported exact publication dates.

## Commercial precedents

### AWS IAM Access Analyzer / Zelkova

Official documentation: https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-checks-validating-policies.html

The documentation states that custom checks compare a policy to a reference policy for new access and that Zelkova translates policies into logical statements evaluated with SMT solvers. This is strong commercial evidence for formal policy reasoning and pre-deployment comparisons. It does not establish multi-step approval-workflow checking.

### SAP Access Control

Official SAP Access Control 12.0 SP23 documentation, *Analyzing Risks When Submitting Access Requests*:

https://help.sap.com/docs/SAP_ACCESS_CONTROL/5cae1bc9a72348389e91183714220e30/0f3ed59eefb04458bfe3ee3a042687fd.html?locale=en-US&state=PRODUCTION&version=12.0.23

The indexed vendor text describes access-request risk/impact analysis, simulation and segregation-of-duties violations. Direct retrieval of the dynamic HTML page returned no readable lines, so this evidence is based on its indexed official documentation text. An additional official PDF describes the same functions:

https://help.sap.com/doc/ca8a8544445e47f5bb0cbc8220ae01b2/12.0.18/en-US/loio8bdd50b2b1f34e049c45ded84788789c_EN.pdf

Overlap: separation-of-duties risk checks and simulation around access requests. This source does not establish that SAP uses GENESIS's bounded-model-checking method.

## Positioning supported by this evidence

GENESIS is an integration-focused prototype for bounded verification of a controlled ServiceNow approval workflow, with replayable evidence and a local decision dashboard. Its particular integration and live demo are project contributions. The general checking techniques, counterexample interfaces, digital-twin terminology and use of AI are not independently novel based on this evidence. Changing platform or solver alone does not demonstrate a new verification method.

Further differentiation would require evidence of capabilities such as faithful real-workflow extraction, broader supported semantics, repeatable target deployment, live concurrency validation, or a measured company pilot. None should be claimed before implementation and validation.

Searches included combinations of workflow verification, separation of duty, satisfiability, Z3, ServiceNow, digital twin and AI across GitHub/LinkedIn/general web search. No full authenticated GitHub code search or private LinkedIn search was performed. Some raw-code and publisher requests failed; this report distinguishes those from readable primary sources. This report was absent from the original 0.2 archive; later repackaged builds include it.
