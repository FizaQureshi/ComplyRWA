# ComplyRWA web interface

A small Streamlit page on top of the ComplyRWA audit. The issuer picks a target configuration, runs the audit, and sees the rule status, grouped findings, the full report and a `report.md` download.

## Run

From the repo root, after `git pull`:

```powershell
cd web
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Python 3.10 or 3.11 both work. No Foundry and no API key are needed. The page opens at http://localhost:8501.

## What it does

Pressing **Run audit** runs `python pipeline/demo.py --target <config> --mode replay` from the repo root and reads `results/demo_<target>/report.json` and `report.md`. The page shows:

- the rule status table, grouped findings, INFO lines and cost
- the findings, with a "side effect" flag where a failure only follows from another rule
- the full report, and a `report.md` download
- an error screen if the command fails, and a "not tested" warning for C03, C04, C07 and V11

## Limits

- The 5 rules (K1, K3, J1, H1, H3) are fixed and read-only. Free-text policies are not supported.
- The audit shows saved evidence in replay mode. It does not run Foundry live.

## Notes

- After running audits, git shows `results/` as modified. Run `git checkout -- results` and do not commit it.
- The "Advanced" box in the sidebar has a test for the error screen (it sends an unknown target).