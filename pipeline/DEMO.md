# ComplyRWA five-minute demo

Run from the `ComplyRWA` folder in Git Bash. `PY=~/.venvs/complyrwa/Scripts/python.exe`

Policy used in every run (5 rules, chosen by the issuer): K1, K3, J1, H1, H3.

| Step | Command | What to say |
|---|---|---|
| 1. Correct setup | `$PY pipeline/demo.py --target C01` | "Nothing is wrong here, and the audit finds nothing." Open `results/demo_C01/report.md` |
| 2. Broken limit | `$PY pipeline/demo.py --target V09` | "The holding-limit module was removed. The token still works, but the cap is gone." Open `results/demo_V09/report.md` |
| 3. One cause, many symptoms | `$PY pipeline/demo.py --target V04` | "No KYC topic is required, so KYC checks pass for everyone." Show that the H3 line is marked as a side effect |

Points to show in each report: policy table, generated test results per rule, grouped findings,
the reproducible test, the INFO line for the known exception, and the cost line.

Notes
- Answers are cached, so repeat runs cost nothing. A new finding costs about $0.0014 (Haiku).
- Test results come from the saved filter runs (`results/filter_d1`, `filter_d2`). They are not re-run live.
- The auditor never sees what a configuration changes (blind mode).
