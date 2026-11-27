# ComplyRWA — Independent Evaluator Pack

**Prepared by:** Member 3 (Charvi) · **Date:** 2026-11-24 · **Branch:** `charvi-reports`

---

## Evaluator Profile

| Field | Details |
|---|---|
| **Name** | [Evaluator Name] |
| **Role** | [e.g. Compliance Analyst, Smart Contract Auditor, Software Engineer, or Student] |
| **Background** | [e.g. Experience with token standards, Web3 compliance, or general programming/review] |
| **Relationship to team** | [Outside the team (independent) / Fallback team member] |

---

## Overview for the Evaluator

Thank you for agreeing to look at this tool.

**What you are evaluating:** ComplyRWA is a tool that checks whether a tokenised investment product (a "real-world asset token") actually follows the compliance rules its issuer wrote. You will read five automatically generated audit reports and tell us whether they are clear and useful to a non-technical token issuer.

**What you do NOT need to know:** You do not need to understand Solidity, smart contracts, or any code. The reports are written in plain English. If something is confusing, please note it — that is valuable feedback.

**How long this takes:** About 30–45 minutes to read the five reports and fill in the table.

**Reports to read:** Five blinded audit reports are provided (labeled Report A through Report E). Open each file in any text viewer.

| Blinded Label | File |
|---|---|
| Report A | `results/demo_C01/report.md` |
| Report B | `results/demo_V04/report.md` |
| Report C | `results/demo_V05/report.md` |
| Report D | `results/demo_V09/report.md` |
| Report E | `results/demo_V12/report.md` |

> *Note for Evaluator:* You are not told in advance which reports describe a problem. Try to decide for yourself whether each one is saying "everything is fine" or "there is a problem."  
> *(Private mapping for team: Report A = C01, Report B = V04, Report C = V05, Report D = V09, Report E = V12. Kept private until review completion.)*

---

## Questionnaire

Please fill in one section per report. Use the 1–5 scale where stated.

**Scale:** 1 = not at all / completely unclear / not actionable · 5 = completely clear / very actionable

---

### Report A

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?** (1–5 + brief note, or N/A if clean)

> *Score:* &nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (test results, reproduction steps) convincing?** (1–5 + brief note, or N/A if clean)

> *Score:* &nbsp;&nbsp; *Note:*

**Q4. How clear is this report? Is anything confusing or unclear?** (1–5 rating + note what was unclear)

> *Score:* &nbsp;&nbsp; *Note:*

**Q5. How actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

### Report B

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?** (1–5 + brief note)

> *Score:* &nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (test results, reproduction steps) convincing?** (1–5 + brief note)

> *Score:* &nbsp;&nbsp; *Note:*

**Q4. How clear is this report? Is anything confusing or unclear?** (1–5 rating + note what was unclear)

> *Score:* &nbsp;&nbsp; *Note:*

**Q5. How actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

### Report C

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?** (1–5 + brief note)

> *Score:* &nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (test results, reproduction steps) convincing?** (1–5 + brief note)

> *Score:* &nbsp;&nbsp; *Note:*

**Q4. How clear is this report? Is anything confusing or unclear?** (1–5 rating + note what was unclear)

> *Score:* &nbsp;&nbsp; *Note:*

**Q5. How actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

### Report D

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?** (1–5 + brief note)

> *Score:* &nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (test results, reproduction steps) convincing?** (1–5 + brief note)

> *Score:* &nbsp;&nbsp; *Note:*

**Q4. How clear is this report? Is anything confusing or unclear?** (1–5 rating + note what was unclear)

> *Score:* &nbsp;&nbsp; *Note:*

**Q5. How actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

### Report E

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> *Your answer:*

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?** (1–5 + brief note)

> *Score:* &nbsp;&nbsp; *Note:*

**Q3. Is the evidence given (test results, reproduction steps) convincing?** (1–5 + brief note)

> *Score:* &nbsp;&nbsp; *Note:*

**Q4. How clear is this report? Is anything confusing or unclear?** (1–5 rating + note what was unclear)

> *Score:* &nbsp;&nbsp; *Note:*

**Q5. How actionable is this report for you as the person responsible for this token?** (1–5)

> *Score:*

---

## Optional Deep-Dive (if you have time)

The following checks are especially valuable because they have only been done by the person who built the system.

### A. Triage labels

The file `review_triage.md` lists findings the AI made on correct (non-broken) tokens, labelled as "stock gap", "real finding" or "false alarm." Read the Per-run table and the label descriptions. Do you agree with the labels? Note any where you would disagree and why.

> *Your answer:*

### B. Generated test alignment

Rule K1 says: *"Only investors with a valid KYC claim from a trusted issuer may receive tokens."* In the V04 report, look at the failing test `test_mintToUnverifiedWalletReverts`. Does the test actually check what the rule says? Is there anything the rule requires that the test does not check?

> *Your answer:*

### C. Explanation accuracy (V12)

In the V12 report, read the "What went wrong" paragraph under the Rule H3 finding, then read the reproduction steps below it. Does the explanation match the steps? Is anything stated that the steps do not support?

> *Your answer:*

---

## Results Summary (filled in by Member 3 after the session)

**Evaluator:** AI assistant (Antigravity / Claude Sonnet 4.6, fallback — no human outsider available at this stage). Full responses in `reports/independent_evaluation.md`.

| Report | Evaluator | Q1 (brief) | Q2 | Q3 | Q4 | Q5 | Key feedback |
|---|---|---|---|---|---|---|---|
| Report A (C01) | AI fallback | No problem — all clean | N/A | N/A | 5/5 | 5/5 | "forcedTransfer" needs a one-line gloss for non-technical readers |
| Report B (V04) | AI fallback | Yes — KYC bypassed; side-effect H3 correctly identified | 4/5 | 5/5 | 4/5 | 4/5 | "direct evidence: 0 of 1" is counterintuitive; "idA" needs introduction |
| Report C (V05) | AI fallback | Yes — country restriction not enforced | 4/5 | 5/5 | 5/5 | 4/5 | Clearest failing report; cap reference in steps minor distraction |
| Report D (V09) | AI fallback | Yes — cap and tracker both broken | 4/5 | 5/5 | 4/5 | 4/5 | Symptom hint excellent; "0 != 500" needs lay explanation |
| Report E (V12) | AI fallback | Yes — forced transfer skips tracker | 5/5 | 5/5 | 5/5 | 5/5 | Most precisely diagnosed report; "both wallets" note minor |

**Average scores (Q2–Q3 for failing reports B–E; Q4–Q5 across all reports A–E):**

| Question | Average |
|---|---|
| Q2 Fix clarity | **4.25 / 5** |
| Q3 Evidence | **5.00 / 5** |
| Q4 Report clarity | **4.60 / 5** |
| Q5 Actionability | **4.40 / 5** |

**Main findings from the session:**

> Evidence quality is high across all five reports (Q3 = 5.0/5). Fix clarity is good but requires a developer intermediary for a non-technical issuer (Q2 = 4.25/5). The side-effect labelling in Report B (V04) works correctly. Report E (V12) is the best-written problem report: one rule, one test, concrete numbers, named function, specific fix. The main recurring gap is technical terminology (forcedTransfer, idA, identity balance) without definition. See `reports/independent_evaluation.md` for full per-report answers including the deep-dive triage review and test-alignment check.

---

*The evaluator's responses will be quoted (with permission) in the final report.*
