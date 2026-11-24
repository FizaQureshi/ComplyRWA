# ComplyRWA — Five-Minute Customer Demo Script

**Presenter:** Member 3 (Charvi)  
**Branch:** `charvi-reports`  
**Date:** 2026-11-24  
**Run order (from `pipeline/DEMO.md`):** C01 → V09 → V04

---

## Before You Start

### Option A — Web App (recommended, already merged into master)

```bash
# From the ComplyRWA folder:
git pull
cd web
py -m venv .venv          # Windows: py -m venv .venv | macOS/Linux: python3 -m venv .venv
# Activate:
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The web app opens in your browser. Pick a target from the dropdown and press **Run audit**. Everything runs in replay mode — no Foundry, no API key needed.

> **Note for the demo:** C03, C04, C07, and V11 show a "not tested" warning. This is expected and documented.

### Option B — Command Line + report.md files

```bash
python pipeline/demo.py --target C01 --mode replay
# Then open results/demo_C01/report.md
```

Replace `C01` with `V09` or `V04` for the next runs. Always use `--mode replay`.

> After any replay run, git may show `results/` as modified.  
> Run `git checkout -- results` before committing. **Do not commit results.**

---

## Demo Run Order

---

### Step 1 — C01: Everything is Correct (1 min 30 s)

**What to say:**

> "Imagine you are a token issuer. You have written five compliance rules for your security token: KYC verification, country restrictions, and a holding cap. You paste those rules into ComplyRWA. Within minutes, it generates tests, runs them, and gives you back a report."
>
> "Let's start with a token that is set up correctly."

**Run:** select **C01** (or run `python pipeline/demo.py --target C01 --mode replay`)  
**Open:** `results/demo_C01/report.md` or the web-app page.

**Show and say:**

| What to point to | What to say |
|---|---|
| **Policy table** (Section 1) | "These are the five rules the issuer typed in — plain English, no code." |
| **Generated properties table** (Section 2) | "The pipeline turned those rules into 20 tests — 4 per rule. Every one passed." |
| **Findings section** | "No findings. The report says the token is compliant." |
| **INFO line** (Section 4) | "There is one known exception: the agent role can override the country restriction. That is by design and the tool labels it as a known exception, not a bug." |
| **Cost line** (Section 5) | "Zero cost here, because nothing needed explaining." |

**Transition:** *"Now let's break something."*

---

### Step 2 — V09: Holding Limit Removed (2 min)

**What to say:**

> "In this configuration, whoever set up the token removed the holding-limit module. The token still works — investors can buy and sell — but the cap is gone. An investor could hold far more than the policy allows."

**Run:** select **V09** (or run `python pipeline/demo.py --target V09 --mode replay`)  
**Open:** `results/demo_V09/report.md` or the web-app page.

**Show and say:**

| What to point to | What to say |
|---|---|
| **Policy table** | "Same five rules. Rule H1 says no investor may hold more than the maximum. Rule H3 says the module's records must match real balances." |
| **Generated properties table** (Section 2) | "H1 and H3 both fail — four tests failed for H1, four for H3." |
| **Finding H1 (Section 3)** | "The report explains in plain English: the mint was not refused even though it would take the investor above the cap. It tells you which function to look at." |
| **Reproduce steps** | "It gives exact steps: mint this amount, check the balance, the check failed. A developer can copy these steps straight into their own environment." |
| **Suggested fix** | "And it tells the issuer what to do: bind the MaxBalanceModule to compliance and set the cap to the right number." |
| **Finding H3** | "H3 flags a second symptom: the module's internal counter stayed at zero after a mint. That is a side effect of the module being unbound." |
| **Cost line** | "Total generation cost: about 3.5 cents. The explainer adds a small fraction per finding." |

**Key message:** *"One configuration change → two rule violations → one clear report with actionable steps."*

---

### Step 3 — V04: One Cause, Many Symptoms (1 min 30 s)

**What to say:**

> "This one is more interesting. Something was changed in the KYC setup — the tool doesn't know what, it only sees the effect. And the effect shows up in rules K1, K3, and even H3."

**Run:** select **V04** (or run `python pipeline/demo.py --target V04 --mode replay`)  
**Open:** `results/demo_V04/report.md` or the web-app page.

**Show and say:**

| What to point to | What to say |
|---|---|
| **Generated properties table** | "Three rules fail: K1, K3, H3. J1 and H1 pass." |
| **Finding K1** | "KYC is broken — an unverified wallet received tokens. The tool caught it in three different tests: mint, transfer, and transfer-to-revoked-claim." |
| **Finding K3** | "The required-topics check also failed, which hints the KYC topic was removed from the required list." |
| **Finding H3 — the side-effect flag** | "H3 also fails. But notice the report groups it as a side effect. The tool says: 'This is probably because the KYC module broke, not because the balance tracker is independently broken.' That stops the issuer from going on a wild-goose chase." |
| **Suggested fix for K1/K3** | "'Compare V04 with C01 for the KYC claim topic and trusted issuer.' The tool tells the issuer exactly where to look." |

**Key message:** *"The tool reasons about causality, not just symptoms. It groups related failures and flags which ones are likely side effects."*

---

## Closing (30 s)

> "What you just saw is the full product loop:  
> — issuer writes rules in plain English  
> — the pipeline generates tests automatically  
> — tests run on the token configuration  
> — a report comes back in plain language with reproduction steps and suggested fixes.  
>
> The whole thing costs under 4 cents for a five-rule policy, takes about 7 minutes end to end, and needs no Foundry or Solidity knowledge from the issuer."

---

## Q&A Prep

| Likely question | Answer |
|---|---|
| "What if my rules are different from these five?" | "The pipeline accepts any rule text. It was tested on KYC, jurisdiction and holding-limit rules. Other rule categories are future work." |
| "Does it run Foundry live?" | "In the web app demo it shows saved evidence in replay mode. A live run needs Foundry installed on the server — that is the productionisation step." |
| "How much does a full audit cost?" | "About \$0.035 (Haiku) to \$0.385 (Sonnet) for test generation. The explainer adds ~\$0.0014 per finding. Total for a 5-rule, 5-finding audit: well under \$1." |
| "What about C03, C04, C07, V11 — why 'not tested'?" | "Those configurations use sub-features (same-identity transfers, Halmos-only checks) that the replay demo does not cover. They are documented and expected." |
| "Is the code open source?" | "The pipeline and test harness are in this repo. MaxBalanceModule is CC-BY-NC-4.0 — non-commercial use only." |

---

## Files to Have Open (web app or file browser)

```
results/demo_C01/report.md
results/demo_V09/report.md
results/demo_V04/report.md
```

Or, if using the web app: start `streamlit run app.py`, keep the browser tab ready, and use the target dropdown.

---

*This script is for the five-minute customer demo in Phase 5. For a longer technical demo, also show `results/benchmark_threeway.md` and `docs/Phase4.md` section 10.*
