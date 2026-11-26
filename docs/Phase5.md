# ComplyRWA: Phase 5 Report (MVP: The Web Interface)
 
**Goal of this report:** document the Phase 5 MVP, the web interface that lets an issuer run the audit and read the result. The other parts of Phase 5 (benchmark write-up, independent evaluation, evaluation report, demo script) belong to Member 3 and are written up in the evaluation report.
 
**Status:** the web interface (step 5.1) is COMPLETE and merged into `master` (status as of 25 Nov 2026). Section 4 lists a few small open items that do not change any result.
 
Pinned system: T-REX tag `4.1.6`, commit `a09cfd38aa257d56db7ff9c90f30e65f125a141b`, Solidity `0.8.17`, Foundry `1.8.7`, Halmos `0.3.3` (see `environment.md`).
 
> **How to read this file.** Section 1 is the step list of Phase 5 and who owns each step. Section 2 covers step 5.1, the web interface, in full. Section 3 records the design decisions. Section 4 is the status and what comes next.
 
---
 
## 1. Phase 5 build order
 
| Step | What | Owner | State |
|---|---|---|---|
| 5.1 | MVP: web interface on top of `pipeline/demo.py` | Member 2 | **Done** |
| 5.2 | Three-way benchmark (hand-written tests, generated tests, LLM-only review) | Member 3 (write-up) | Numbers done in Phase 4 (section 10.6). Write-up in the evaluation report |
| 5.3 | Independent evaluation (at least one person outside the team) | Member 3 | In the evaluation report |
| 5.4 | Short evaluation report | Member 3 | Written by Member 3 |
| 5.5 | Five-minute customer demo | All three | The page is ready. Script and recording: Member 3 with Members 1 and 2 |
 
This file documents step 5.1 only. Steps 5.2 to 5.5 are written up by their owners.
 
---
 
## 2. Step 5.1: Web interface (MVP)
 
**Goal:** give an issuer a simple page to pick a target, run the audit and read the result, without a terminal.
 
**Status: COMPLETE.** Merged into `master` in two pull requests: the first version (merge commit `270d4b1`, 24 Nov 2026) and the polish (merge commit `f799745`, 25 Nov 2026). Files: `web/app.py`, `web/requirements.txt`, `web/README.md`, and one line in `.gitignore` (`web/.venv/`).
 
### 2.1 Why it was needed
 
The brief asks for a minimal interface where a user selects a target, runs an audit and gets a report to download. The Phase 4 pipeline is a command (`pipeline/demo.py`) that writes `report.json` and `report.md`. The page puts a screen on top of that command. It does not call a model, does not need a key and does not run Foundry.
 
### 2.2 What was built
 
| Part | What it does |
|---|---|
| Target dropdown | 21 entries, each shown as ID and name (for example `V07 – Bug: Country rule removed`), with a help text under it. C03, C04, C07 and V11 carry the suffix "(not tested)" |
| Policy table | The 5 fixed rules K1, K3, J1, H1 and H3, read-only |
| Run audit | A progress list with the five step names that `demo.py` prints, shown while the command runs |
| Result banner | One of: failed, not tested, problems found, no problems with notes, no findings |
| Rule status tab | Counts (checked, passed, failed, not tested), the rule table (rule, policy, tests, failed, status, severity, note), grouped findings, INFO lines and the cost line |
| Findings tab | The finding text, direct evidence, failing tests, the side-effect flag and the reproducible test |
| Full report tab and download | `report.md` shown on the page, and a download button named after the target (for example `report_V04.md`) |
| Error screen | The stage and the message when the audit fails |
| Blind audit option | A checkbox (sidebar, Advanced) that hides what each configuration changes, so the dropdown shows only `Configuration V07` |
 
### 2.3 How it works
 
1. The user picks a target from the fixed dropdown. The target is never typed as free text.
2. The page runs the command from the repo root. It always passes `--mode replay`, because the default mode is live and can spend money:
```
python pipeline/demo.py --target <config> --mode replay
```
3. While the command runs, the page shows the progress list.
4. The page checks the exit code first. Exit 0 means `report.json` exists and has `"status": "ok"`. A non-zero exit means `report.json` holds `"status": "error"` with a message, which the page shows on the error screen. If the file is missing, the page shows the last line of the command's output.
5. It reads only `results/demo_<target>/report.json` and `report.md`. It does not read `results/explain_d1+d2_blind/`, which is overwritten on every run.
6. It shows these fields:
   | Field | Used for |
   |---|---|
   | `target`, `model`, `mode` | The caption under the banner |
   | `rules.<ID>` (policy, tests_run, failed, status, severity) | The rule status table |
   | `groups` | The grouped findings list |
   | `info` | The INFO boxes |
   | `findings.<ID>` (severity, text, direct_evidence, failing_tests, reproducible_test) | The Findings tab and the note column |
   | `cost` | The cost line |
   | `report.md` | The Full report tab and the download |
7. **Side effect.** `findings.<ID>.direct_evidence.direct == 0` means every failure of that rule only follows from another rule's problem (for example H3 on V04). The page writes "side effect, not a separate problem" in the note column and on the finding.
8. **Not tested.** For C03, C04, C07 and V11 every rule has status `NOT_RUN` and `tests_run` 0. The page shows a warning that this is not a clean result. It also shows this warning for these four targets by name, whatever the status says.
Progress step names (they match the five lines `demo.py` prints): policy input, generated properties, executed tests, explaining the failures, building the audit report.
 
### 2.4 How to run
 
From the repo root, after `git pull`:
 
```
cd web
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
 
Python 3.10 and 3.11 both work. No Foundry and no API key are needed. The page opens at `http://localhost:8501`. After running audits, git shows files under `results/` as modified. Run `git checkout -- results` and do not commit them.
 
### 2.5 Proof
 
All 21 targets and the bad target V99 were checked by hand on a Windows laptop with Python 3.10 in a plain venv, with no Foundry and no API key. The expected results are the table that Member 1 gave for the replay command.
 
| Target | Expected | Observed |
|---|---|---|
| C01, C02, C05, C06, C08 | all rules PASS | Same |
| C03, C04, C07, V11 | all rules `NOT_RUN` | Same. Warning "Not tested", 5 of 5 rules not tested |
| V01, V02 | K1, K3 and H3 fail | Same |
| V03 | K1 and H3 fail | Same |
| V04 | K1, K3 and H3 fail. H3 is a side effect | Same. Two groups ("KYC requirement missing or bypassed" with K1 and K3, and "Holding limit not enforced or tracked wrongly" with H3). The H3 note reads "side effect, not a separate problem" |
| V05, V06, V07, V08 | only J1 fails | Same. For V07 one group ("Jurisdiction restriction not enforced" with J1) |
| V09, V10 | H1 and H3 fail | Same |
| V12 | only H3 fails | Same |
| V13 | only H1 fails | Same |
| V99 (the "Test the error screen" box in Advanced) | exit 1 and "unknown configuration V99" | Same. The error screen shows stage `demo` and the message |
 
The dropdown names and help texts match the table that Member 1 shared.
 
### 2.6 Observations
 
1. **The console line and the JSON can differ.** For C03 the command first printed `PASS` for rules that never ran, while `report.json` already said `NOT_RUN`. Member 1 fixed the console line (commit `2aea6c6`). The page reads the JSON, so it was right from the start.
2. **Running an audit rewrites files under `results/`.** Git then shows them as modified, and a later `git merge` stops with "local changes would be overwritten". `git checkout -- results` before a merge fixes it.
3. **A replay takes about a second per target** (Member 1). The progress list is shown while the command runs and finishes when it does.
4. **Unknown values are shown as they are.** `status` and `severity` can be other strings than PASS, FAIL, NOT_RUN and HIGH. The page does not fail on them and shows them in a neutral colour.
5. **Only the four named targets are not tested.** A correct reading of the page therefore needs the "(not tested)" label in the dropdown and the banner together.
### 2.7 Problems met and fixes
 
| # | Problem | Fix |
|---|---|---|
| 1 | The first plan used `complyrwa.py audit`, `policy.json` and `results.json` (from `RESULTS_FORMAT.md`). The real pipeline uses `pipeline/demo.py`, no policy file and `report.json` | The page was rebuilt around the real command and files |
| 2 | The 5 rule rows were editable, but the command takes no rule list | The rows became a read-only table |
| 3 | A separate backend (FastAPI) was planned | Not needed. The page runs the command itself |
| 4 | C03 printed `PASS` on the console for rules that never ran | Member 1 fixed the console line. The page keeps its own "not tested" warning |
| 5 | The `$` signs in the cost line were drawn as a formula | The dollar signs are escaped |
| 6 | `NOT RUN` broke into two lines in the status column, and two table headers wrapped | A non-breaking space was used and the headers were shortened ("Tests", "Failed") |
| 7 | A `.streamlit/config.toml` removed the theme choice and the menu | The file was deleted. The sidebar width and the centred content are set with a small piece of CSS in the page |
| 8 | A `git merge` was stopped by modified files under `results/` | `git checkout -- results` before the merge |
 
### 2.8 Limits
 
1. **Only the 5 rules K1, K3, J1, H1 and H3 can be audited.** The command takes no rule list, and the saved tests were made for exactly these texts, so editing a row would change nothing. Free-text policies are not supported. Other rules would need a `--rules` option in `demo.py`, limited to the rules that have generated tests.
2. **The page shows saved evidence from replay mode.** It does not generate tests and does not run Foundry live.
3. **The user cannot choose a local ERC-3643 project.** The pipeline reads saved results for the pinned T-REX 4.1.6 only.
4. **C03, C04, C07 and V11 are not tested** by the saved results. "No findings" on any target only means no findings for these 5 rules.
5. **Blind mode is partial.** It hides the configuration names and help texts, but the dropdown still shows "(not tested)" for the four targets above.
6. **The page depends on the `report.json` field names.** If they change, the page must change. Member 1 has agreed to announce any change.
7. **One audit at a time.** Every run appends to a shared log file, and the cost numbers would mix if two ran together.
8. **Hand testing only.** All 21 targets were checked by hand (section 2.5). There is no automatic test of the page in the repo.
### 2.9 How to reproduce
 
```
cd web
streamlit run app.py                                           (pick a target, press Run audit)
python pipeline/demo.py --target V04 --mode replay             (the same audit without the page, from the repo root)
git checkout -- results                                        (after every run)
```
 
To see the error screen, open Advanced in the sidebar, tick "Test the error screen" and press Run audit.
 
---
 
## 3. Design decisions for Phase 5 (web interface)
 
1. **Streamlit, not React with FastAPI.** The page only runs one command and shows files, so it needs no separate backend. It is all Python and was the safer choice for the time available.
2. **Replay mode only.** The page always passes `--mode replay`. Replay needs no Foundry, no API key and costs nothing (Member 1). The page says that it shows saved evidence.
3. **The 5 rows are fixed and read-only** (Member 1). The command takes no rule list.
4. **The target comes from a fixed dropdown of 21.** Free text is never sent to the command.
5. **The page reads only `report.json` and `report.md`, and checks the exit code first** (Member 1).
6. **C03, C04, C07 and V11 are shown as "not tested", not as "no findings"** (Member 1). The warning is also tied to these names.
7. **A side effect is shown as a note**, taken from `findings.<ID>.direct_evidence`.
8. **Blind audit is optional and off by default.** The names are shown for the customer demo. The checkbox hides them for a realistic audit and for the independent evaluator.
9. **One audit at a time.**
10. **The web part lives in `web/`** (plus one line in `.gitignore`). The page does not change `pipeline/` or `results/`.
---
 
## 4. Status and next
 
- [x] 5.1 Web interface: merged into `master`, checked by hand on all 21 targets and the error case (section 2.5)
Steps 5.2 to 5.5 (benchmark write-up, independent evaluation, evaluation report, demo script and recording) are owned by Member 3 and are written up in the evaluation report, not in this file. The page is ready for the evaluation and for the demo.
 
Open items for the web interface:
 
1. Ideas that were discussed and not built: a table of all 21 configurations in one view, quick buttons for the demo targets, short explanations for terms such as side effect and severity.
2. Update this file if any of these are built, or if the `report.json` field names change.
 