# ComplyRWA — Five-Minute Customer Demo Script

**Presenter:** Member 3 (Charvi) · **Branch:** `charvi-reports` · **Date:** 2026-11-24  
**Run order (from `pipeline/DEMO.md`):** C01 → V09 → V04

---

## Before You Start

### Option A — Web App (recommended)

```bash
git pull
cd web
py -m venv .venv          # Windows: py -m venv .venv
# Activate: Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens in the browser. Pick a target from the dropdown and press **Run audit**. The web demo uses saved evidence in replay mode and does not run Foundry live (no Foundry and no API key needed).

> **Note:** C03, C04, C07 and V11 show a "not tested" warning. This is expected — those four configurations start with balances already set, so scenario tests are skipped and only property tests run on them.

### Option B — Command line

```bash
python pipeline/demo.py --target C01 --mode replay
# Then open results/demo_C01/report.md
```

Replace `C01` with `V09` or `V04`. Always use `--mode replay`.

> **Safe Git workflow:** Check `git status` first to confirm you have no results changes to preserve, then run `git checkout -- results` before `git add reports/`. Do not commit `results/`.

---

## Demo Run Order

---

### Step 1 — C01: Everything is Correct (1 min 30 s)

**What to say:**

> "Imagine you are a token issuer. You have written five compliance rules for your security token: KYC verification, country restrictions, and a holding cap. You paste those rules into ComplyRWA. Within minutes, it generates tests, runs them, and gives you a report."
>
> "Let's start with a token that is set up correctly."

**Run:** select **C01** in the web app (or `python pipeline/demo.py --target C01 --mode replay`)

**Show and say:**

| What to point to | What to say |
|---|---|
| **Policy table** (Section 1) | "These are the five rules the issuer typed in — plain English, no code." |
| **Generated properties table** (Section 2) | "The pipeline turned those rules into 20 tests — 4 per rule. Every one passed." |
| **Findings section** | "No findings. The report says the token is compliant." |
| **INFO line** (Section 4) | "One known exception is listed: the agent role can override the country restriction by design. The tool labels it as a known exception, not a bug." |
| **Cost line** (Section 5) | "Zero cost here — nothing failed, so nothing needed explaining." |

**Transition:** *"Now let's break something."*

---

### Step 2 — V09: Holding Limit Removed (2 min)

**What to say:**

> "In this configuration, the holding-limit module was removed. The token still works — investors can buy and sell — but the cap is gone. An investor could hold far more than the policy allows."

**Run:** select **V09** (or `python pipeline/demo.py --target V09 --mode replay`)

**Show and say:**

| What to point to | What to say |
|---|---|
| **Policy table** | "Same five rules. Rule H1 says no investor may hold more than the maximum. Rule H3 says the module's records must match real balances." |
| **Generated properties table** | "H1 and H3 both fail." |
| **Finding H1** | "The report says the mint was not refused even though it would take the investor above the cap. It tells you which functions to look at and gives exact reproduction steps." |
| **Finding H3** | "H3 flags a second symptom: the module's internal counter stayed at zero after a mint." |
| **Suggested fix** | "And it tells the issuer what to do: bind the MaxBalanceModule to compliance and set the cap to the right number." |
| **Cost line** | "Total generation cost: about 3.5 cents. That is for all 10 rules across the whole benchmark. The five rules used in this demo cost less." |

**Key message:** *"One configuration change → two rule violations → one clear report with actionable steps."*

---

### Step 3 — V04: One Cause, Many Symptoms (1 min 30 s)

**What to say:**

> "This one is more interesting. Something was changed in the KYC setup. The tool doesn't know what — it only sees the effect — and the effect shows up across multiple rules."

**Run:** select **V04** (or `python pipeline/demo.py --target V04 --mode replay`)

**Show and say:**

| What to point to | What to say |
|---|---|
| **Generated properties table** | "Three rules fail: K1, K3, H3. J1 and H1 pass." |
| **Finding K1** | "KYC is broken — an unverified wallet received tokens. The tool caught it in three different tests: mint, transfer, and transfer-to-revoked-claim." |
| **Finding K3** | "The required-topics check also failed, suggesting the KYC topic is not required." |
| **Finding H3 — the note at the bottom** | "Look at the last line: 'All failing H3 tests are side effects of the KYC failure above. No separate holding-limit problem is shown.' The report tells the issuer not to chase a second problem that isn't there." |
| **Suggested fix for K1/K3** | "'Compare V04 with C01 for the KYC claim topic and trusted issuer.' The tool tells the issuer exactly where to look." |

**Key message:** *"The report groups related failures and notes when failures look like side effects of another failure."*

---

## Closing (30 s)

> "What you just saw is the full product loop:
> — issuer writes rules in plain English
> — the pipeline generates tests automatically
> — tests run on the token configuration
> — a report comes back in plain language with reproduction steps and suggested fixes.
>
> The five rules used in the demo are fixed and shown in the web app. The underlying pipeline supports 10 rules across three categories: KYC, jurisdiction, and holding limits."

---

## Q&A Prep

| Likely question | Answer |
|---|---|
| "Can I write my own rules?" | "The web demo has 5 fixed read-only rules. The pipeline itself supports 10 rules across three categories — extending to new rule categories is future work." |
| "Does it run Foundry live?" | "In the web app demo it shows saved evidence in replay mode. A live run needs Foundry installed on the server — that is the productionisation step." |
| "How much does a full audit cost?" | "Generation cost depends on the model and number of rules. Haiku costs about \$0.0035 per rule; Sonnet about \$0.0385. The explainer adds ~\$0.0014 per finding." |
| "Why do C03, C04, C07 and V11 show 'not tested'?" | "Those four configurations start with balances already set. Scenario tests assume an empty start and are skipped on them; only property tests run. This is documented and expected." |
| "Is the code open source?" | "The pipeline and tests are in the project repository. Files derived from T-REX are GPL-3.0, and MaxBalanceModule is CC-BY-NC-4.0." |

---

## Files Needed for the Demo

```
results/demo_C01/report.md
results/demo_V09/report.md
results/demo_V04/report.md
```

Or start the web app with `streamlit run app.py` and keep the browser tab ready.

---

*This script is for the five-minute customer demo in Phase 5. For a longer technical demo, also show `results/benchmark_threeway.md` and `docs/Phase4.md` section 10.*
