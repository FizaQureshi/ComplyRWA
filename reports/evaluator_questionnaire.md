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

**Reports to read:** The five `report.md` files are attached to this document. Open each one in any text viewer.

| Label | File |
|---|---|
| C01 | `C01_report.md` |
| V04 | `V04_report.md` |
| V05 | `V05_report.md` |
| V09 | `V09_report.md` |
| V12 | `V12_report.md` |

> You are not told in advance which reports describe a problem. Try to decide for yourself whether each one is saying "everything is fine" or "there is a problem."

---

## Questionnaire

Please fill in one section per report. Use the 1–5 scale where stated.

**Scale:** 1 = not at all / completely unclear / not actionable · 5 = completely clear / very actionable

---

### Report C01

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

### Report V04

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

### Report V05

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

### Report V09

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

### Report V12

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

| Report | Evaluator | Q1 (brief) | Q2 | Q3 | Q4 | Q5 | Key feedback |
|---|---|---|---|---|---|---|---|
| C01 | | | — (N/A) | — (N/A) | /5 | /5 | |
| V04 | | | /5 | /5 | /5 | /5 | |
| V05 | | | /5 | /5 | /5 | /5 | |
| V09 | | | /5 | /5 | /5 | /5 | |
| V12 | | | /5 | /5 | /5 | /5 | |

**Average scores (Q2–Q3 for broken reports V04–V12; Q4–Q5 across all reports):**

| Question | Average |
|---|---|
| Q2 Fix clarity | |
| Q3 Evidence | |
| Q4 Report clarity | |
| Q5 Actionability | |

**Main findings from the session:**

> *[To be filled in by Member 3]*

---

*The evaluator's responses will be quoted (with permission) in the final report.*
