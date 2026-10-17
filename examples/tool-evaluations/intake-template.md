# Candidate intake (complete before any installation)

Copy this form into a research note and add a `TOOL-<NAME>` row to tracker §G
before running a throwaway experiment. The row starts at `proposed / UNEVALUATED`.
An experiment install never authorizes a project dependency. Review an ADOPT or
ADAPT decision before dependency changes.

| Field | Required evidence |
|---|---|
| ID / owner task / date | `TOOL-…`, tracker task, evaluator and date |
| Intended contribution | Specific pipeline step and missing capability |
| Official URL / pin | Upstream docs/source; exact release and commit or artifact hash |
| Licence | Licence file at the pin; obligations and relevant bundled dependencies |
| Maintenance / maturity | Release history and limitations observed, separate from judgment |
| Existing installation | `command -v`, package listing; don't mistake configuration for access |
| macOS arm64 / Python 3.11 + 3.13 | Actual runs or wheel tags; distinguish verified from unknown |
| Offline operation | What works after provisioning; network blocked mechanism and remaining gaps |
| Installation | Disposable directory, pinned commands, browser/native/system prerequisites |
| Integration complexity | Proposed adapter boundary; effect on canonical HouseModel/domain |
| Security / privacy | Inputs sent, network destinations, processes, local artifacts, consent needs |
| Proof of value | Synthetic inputs, closed-form ground truth, defect cases, reproducible command |
| Observed results | Raw artifacts and metrics; `measured`, `simulated`, `ai_judgment`, `not_checked` |
| Failure / unknowns | Exceptions, false positives, untested platforms and unsupported semantics |
| Decision | UNEVALUATED / ADOPT / ADAPT / REJECT / DEFER; evidence and scope |
| Highest verified | Mentioned → proposed → installed → configured → accessible → tested → integrated → used successfully |
| Independent review | Reviewer, rerun evidence, licence check; dependency changes only afterward |
