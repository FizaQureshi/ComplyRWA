# ComplyRWA — Independent Evaluator Pack

**Prepared by:** Member 3 (Charvi)  
**Date:** 2026-11-24  
**Branch:** `charvi-reports`

---

## Overview for the Evaluator

Thank you for agreeing to look at this tool.

**What you are evaluating:** ComplyRWA is a tool that checks whether a tokenised investment product (a "real-world asset token") actually follows the rules its issuer wrote. You will read five automatically generated audit reports and tell us whether they are clear and useful to a non-technical token issuer.

**What you do NOT need to know:** You do not need to understand Solidity, smart contracts, or any code. The reports are written in plain English. If something is confusing, that is valuable feedback — please note it.

**How long this takes:** About 30–45 minutes to read the five reports and fill in the table.

**Reports to read (open these files in any text viewer or the web app):**

| Label | File | What to expect |
|---|---|---|
| C01 | `results/demo_C01/report.md` | A clean token — no problems found |
| V04 | `results/demo_V04/report.md` | A broken token — multiple compliance rules violated |
| V05 | `results/demo_V05/report.md` | A broken token — wrong country allowed |
| V09 | `results/demo_V09/report.md` | A broken token — holding cap not enforced |
| V12 | `results/demo_V12/report.md` | A broken token — a subtle accounting bug |

> You are not told in advance which reports describe a problem. Try to decide for yourself whether each one is saying "everything is fine" or "there is a problem."

---

## Questionnaire

Please fill in one row per report. Use the 1–5 scale where stated. Write freely in the text columns.

### Scale reference

| Score | Meaning |
|---|---|
| 1 | Not at all / completely unclear / not actionable |
| 2 | Slightly / somewhat unclear |
| 3 | Moderately |
| 4 | Mostly clear / mostly actionable |
| 5 | Completely clear / very actionable |

---

### Report C01

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you know what should be fixed and roughly who should fix it?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (the test results, the reproduction steps) convincing to you?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q4. Is anything in this report confusing or unclear? Please note exactly what.**

> *Your answer:*

**Q5. Overall, how actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

### Report V04

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you know what should be fixed and roughly who should fix it?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (the test results, the reproduction steps) convincing to you?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q4. Is anything in this report confusing or unclear? Please note exactly what.**

> *Your answer:*

**Q5. Overall, how actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

### Report V05

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you know what should be fixed and roughly who should fix it?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (the test results, the reproduction steps) convincing to you?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q4. Is anything in this report confusing or unclear? Please note exactly what.**

> *Your answer:*

**Q5. Overall, how actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

### Report V09

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you know what should be fixed and roughly who should fix it?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (the test results, the reproduction steps) convincing to you?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q4. Is anything in this report confusing or unclear? Please note exactly what.**

> *Your answer:*

**Q5. Overall, how actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

### Report V12

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you know what should be fixed and roughly who should fix it?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (the test results, the reproduction steps) convincing to you?** (1–5 and brief note)

> *Score:* &nbsp;&nbsp;&nbsp; *Note:*

**Q4. Is anything in this report confusing or unclear? Please note exactly what.**

> *Your answer:*

**Q5. Overall, how actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

## Optional Deep-Dive (if you have time)

If you can spare another 15–20 minutes, the following checks are especially valuable because they have only been done by the person who built the system:

### A. Triage labels (`results/review_triage.md`)

The file lists findings the AI made on clean (non-broken) tokens, labelled as either:
- **Stock gap** — a real known issue in the underlying framework, not a false alarm
- **Real finding** — a genuine compliance gap in the clean configuration, not a false alarm
- **False alarm** — the AI was wrong

Please read the "Per run" table and the descriptions of each category. Do you agree with the labels? Note any where you would disagree and why.

> *Your answer:*

### B. Generated test alignment

The pipeline generates tests from plain-English rules. For example, rule K1 says *"Only investors with a valid KYC claim from a trusted issuer may receive tokens."* Open `results/demo_V04/report.md` and look at the failing test `test_mintToUnverifiedWalletReverts`. Does the test actually check what the rule says? Is there anything the rule requires that the test does not check?

> *Your answer:*

### C. Explanation accuracy (V12)

Open `results/demo_V12/report.md` and read the "What went wrong" paragraph under Finding F1. Then read the reproduction steps. Does the explanation match the steps? Is anything stated that the steps do not support?

> *Your answer:*

---

## Results Summary (to be filled in by Member 3 after the session)

| Report | Evaluator name | Q1 (brief) | Q2 | Q3 | Q4 | Q5 | Key feedback |
|---|---|---|---|---|---|---|---|
| C01 | | | | | | | |
| V04 | | | | | | | |
| V05 | | | | | | | |
| V09 | | | | | | | |
| V12 | | | | | | | |

**Average scores (Q2–Q5 across V04, V05, V09, V12):**

| Question | Average |
|---|---|
| Q2 Fix clarity | |
| Q3 Evidence | |
| Q4 Report clarity | |
| Q5 Actionability | |

**Main findings from the session:**

> *[To be filled in by Member 3]*

---

*This questionnaire is part of the Phase 5 independent evaluation. The evaluator's responses will be quoted (with permission) in the final report.*
