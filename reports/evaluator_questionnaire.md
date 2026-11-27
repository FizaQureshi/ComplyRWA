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
| Report A | `report_A.md` |
| Report B | `report_B.md` |
| Report C | `report_C.md` |
| Report D | `report_D.md` |
| Report E | `report_E.md` |

> *Note for Evaluator:* You are not told in advance which reports describe a problem. Try to decide for yourself whether each one is saying "everything is fine" or "there is a problem."

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

Rule K1 says: *"Only investors with a valid KYC claim from a trusted issuer may receive tokens."* In Report B, look at the failing test `test_mintToUnverifiedWalletReverts`. Does the test actually check what the rule says? Is there anything the rule requires that the test does not check?

> *Your answer:*

### C. Explanation accuracy (Report E)

In Report E, read the "What went wrong" paragraph under the Rule H3 finding, then read the reproduction steps below it. Does the explanation match the steps? Is anything stated that the steps do not support?

> *Your answer:*

---

*Thank you for your feedback. Results and target mappings are recorded separately by Member 3 in `reports/independent_evaluation.md`.*
