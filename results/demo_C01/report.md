# ComplyRWA audit report: C01

Audit target: configuration `C01` (cause hidden from the auditor). Model: haiku. Mode: live.

## 1. Policy input

| Rule | Policy |
|---|---|
| K1 | Only investors with a valid KYC claim from a trusted issuer may receive tokens. |
| K3 | At least one KYC claim topic must be required. |
| J1 | Investors registered in a restricted country may not receive tokens. |
| H1 | No investor may hold more than the maximum allowed tokens. |
| H3 | The holding-limit module's balance records must match the real token balances. |

## 2. Generated properties and execution results

| Rule | Generated tests run | Failed | Status |
|---|---|---|---|
| K1 | 4 | 0 | PASS |
| K3 | 4 | 0 | PASS |
| J1 | 4 | 0 | PASS |
| H1 | 4 | 0 | PASS |
| H3 | 4 | 0 | PASS |

## 3. Findings grouped by symptom

No generated test failed on this configuration. No findings.
## 4. Known exceptions

INFO: J1 bypassed via forcedTransfer (agent-only path). Classified as a known exception, not a vulnerability. (Result of a fixed probe test, not generated from the policy.)

## 5. Cost and time

- Explainer LLM calls this run: 0; cost paid $0.0000; cost when first made $0.0000; model seconds 0
- Demo wall time: 0 s
- Generation cost is in `results/benchmark_generated.md` (tests were generated once and replayed).
