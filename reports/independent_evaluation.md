# ComplyRWA — Independent Evaluation Record

**Evaluation date:** 2026-11-27  
**Branch:** `charvi-reports`  
**Recorded by:** Member 3 (Charvi)

---

## Evaluator Profile

| Field | Details |
|---|---|
| **Name** | Poorvi |
| **Role** | Independent reviewer — outside the project team |
| **Background** | General software and review background; no prior knowledge of the ComplyRWA codebase, the seeded variants, or the benchmark results |
| **Relationship to team** | Outside the team (independent) |

---

## Reports Evaluated

| Blinded Label | Source file | Assignment |
|---|---|---|
| Report A | `results/demo_C01/report.md` | C01 — baseline, all rules clean |
| Report B | `results/demo_V04/report.md` | V04 — KYC topics list emptied |
| Report C | `results/demo_V05/report.md` | V05 — wrong country restricted |
| Report D | `results/demo_V09/report.md` | V09 — MaxBalanceModule removed |
| Report E | `results/demo_V12/report.md` | V12 — forcedTransfer skips tracker |

> *The blinded label-to-target mapping was kept private until after all five reports were read. The evaluator was not told in advance which reports describe a problem.*

---

## Questionnaire Responses

**Scale used:** 1 = not at all / completely unclear / not actionable · 5 = completely clear / very actionable

---

### Report A (C01 — clean)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> This report says the token configuration is compliant. Twenty automated tests were run across five rules (KYC, required topics, country restriction, holding cap, balance tracking) and every one passed. There is no finding. One known exception is noted: the agent role can bypass the country rule using a forced transfer, but that is explicitly classified as a known exception and not flagged as a vulnerability. Overall message: everything is as expected.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* N/A — no problem found  
> *Note:* Clean report. The known exception is explained clearly enough that a non-technical reader would understand it means "this is by design, not a bug."

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* N/A — no failing tests  
> *Note:* The test table (20 tests run, 0 failed) is concise. No reproduction steps needed.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 5  
> *Note:* The clean report is easy to read. The only mild confusion for a non-technical reader is the phrase "forcedTransfer (agent-only path)" in Section 4 — it uses a technical term without explanation. A one-sentence gloss such as "this means only an authorised administrator can override the rule" would help.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 5  
> *Note:* "No findings" is unambiguous. The INFO line gives enough context to understand the known exception and decide whether it is acceptable.

---

### Report B (V04 — KYC bypassed)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Yes, there is a problem — in fact multiple related problems, all apparently caused by the same underlying issue. The token let an unverified investor (Mallory) receive tokens by both minting and transfer. It also let tokens be transferred to an investor whose KYC claim had been revoked. Both of these should have been blocked. Additionally, the balance tracker for the holding-limit module drifted — but the report explicitly states this is a side effect of the KYC failure, not a separate bug. Three rules are flagged: K1 (KYC verification), K3 (required topics list), and H3 (tracker accuracy). The report says the root cause is unknown from the output alone, and suggests comparing this configuration against the clean baseline to find which KYC setting is wrong.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* 4  
> *Note:* The report names the affected functions (token.mint, token.transfer, ctr.getClaimTopics) and gives a specific, actionable suggestion: add the KYC claim topic with `ctr.addClaimTopic(KYC_TOPIC)` and compare the trusted-issuer and identity-check settings between V04 and C01. That is enough for a developer to start investigating. The score is 4 rather than 5 because the report correctly notes the root cause is unknown — a reader would know *what area* to look at but not the exact line to change. For a non-technical issuer the phrase "compare V04 with C01 for the KYC claim topic" may need translation.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* 5  
> *Note:* Three of three failing K1 tests are listed. The reproduction steps for `test_mintToUnverifiedWalletReverts` are step-by-step and unambiguous: mint 1 token to Mallory, expect a specific revert message, observe the call succeeds. The Solidity test code is included. For H3, the report correctly identifies the failure as a side effect and says "direct evidence: 0 of 1" — this honesty is a strength. A reader can immediately distinguish which failures are primary and which are downstream.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 4  
> *Note:* The grouping by rule (K1, K3, H3 under separate headings) is logical. The side-effect note for H3 is well placed and clearly worded. Two things could be improved for a non-technical reader: (a) the phrase "idA" (Alice's identity) is used without being introduced, and (b) the note "direct evidence: 0 of 1 failing tests" is counterintuitive — it means the test failed for a secondary reason, not that the evidence is weak. A brief parenthetical explanation would help.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 4  
> *Note:* The report tells the responsible person that KYC is broken, which functions are affected, and where to look. The specific suggestion ("add the KYC claim topic") is directly actionable. The score is 4 rather than 5 because the precise configuration setting that is wrong is not identified — the report says the cause is not known from the output, which is honest but means the issuer must do some investigation rather than apply a one-line fix.

---

### Report C (V05 — wrong country restricted)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Yes. The country restriction rule is not working. Three different methods of sending tokens to a restricted-country investor all succeeded when they should have been blocked: minting directly, a regular transfer, and a transferFrom. The KYC checks are fine — the problem is specifically with the jurisdiction restriction. The report states the cause is not known from the output, and suggests checking that the country restriction module is bound to the compliance contract and that the restricted-country value is set correctly.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* 4  
> *Note:* The fix area is clear — check that the country restriction module is bound and that the right country code is configured. The report names the three affected functions. The score is not 5 because it doesn't tell the reader *which* country code should be restricted or what value is currently set, so the developer still needs to look up the configuration.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* 5  
> *Note:* Three of three failing tests are listed. The reproduction steps for `test_mintToRestrictedCountryIsBlocked` are precise and clear: set the investor's country, then mint, expect a specific revert message ("Compliance not followed"), observe the call succeeds instead. The Solidity test code matches the steps exactly. The failing assertion messages are also shown, which confirm the tokens actually moved.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 5  
> *Note:* This is the clearest of the failing reports. One rule fails, three tests demonstrate it in three different transaction types (mint, transfer, transferFrom), and the reproduction steps are written in plain English. The only minor issue is the phrase "V05's cap is not given" in step 3 of the reproduction — a reader might wonder if the cap matters. A note clarifying "the cap is irrelevant to this test; we just need any positive amount" would be a small improvement.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 4  
> *Note:* The responsible person is told exactly what failed and which module to inspect. The slight limitation is that the report says "check that the restricted-country variable is set as intended" without saying what the intended value should be — that is in the policy, not the report, so the issuer needs to look it up themselves.

---

### Report D (V09 — holding limit removed)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Yes, there is a serious problem. The holding cap is not being enforced at all, and the internal balance tracker is completely broken. Minting tokens to Bob above the cap succeeded when it should have been refused. The tracker shows 0 for every investor even after real tokens have been minted — which means the cap check always sees a zero balance and never blocks anything. All eight H1 and H3 tests failed. The report provides a symptom hint that is particularly useful: "the module's tracked balance stayed at 0 after real mints, so the module is not being notified — check that compliance.getModules() lists MaxBalanceModule." This strongly implies the MaxBalanceModule is not bound to the token at all.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* 4  
> *Note:* The suggested fix is specific: check that MaxBalanceModule is bound to compliance, check that the cap check runs on both mint and transfer, and confirm the cap value. The symptom hint effectively tells a developer *how to diagnose* the problem. The score is not 5 because the cap value for V09 is said to be "not given in the inputs," which a developer would need to find separately.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* 5  
> *Note:* The report is thorough. For H1, the reproduction steps are numbered and clear. For H3, the specific assertion failure messages are given ("idA tracked != real: 0 != 100" for all four tests), which makes the nature of the bug immediately obvious without code expertise. The "direct evidence: 2 of 4" for H1 and "4 of 4" for H3 is an honest summary. The Solidity test code is provided.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 4  
> *Note:* The report is well-structured and distinguishes H1 (cap not enforced) from H3 (tracker broken). The "0 != 500" failure message for two H1 tests could confuse a non-technical reader — it's explained as "the module's counter did not move," which is good, but requires understanding what a "counter" is. The symptom hint in the H3 section ("Check that compliance.getModules() lists MaxBalanceModule") is the most actionable single sentence in any of the five reports; a non-technical reader would still understand it means "make sure the module is turned on."

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 4  
> *Note:* The report clearly conveys: the cap is not working, tokens can be held without limit, and the most likely cause is that the enforcement module is not connected. That is enough for a responsible party to escalate to their developer with a specific diagnosis. The score is 4 rather than 5 because "confirm the cap value" is left open — the issuer would need to refer to the original configuration document to know what the cap should be.

---

### Report E (V12 — forcedTransfer skips tracker)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Yes, there is a subtle but real problem. Everything works correctly for ordinary mints, burns, and transfers — those all pass. The issue surfaces only when a forced transfer is used: after a forced transfer, the internal tracker for Alice's holdings shows 75 tokens, but her actual balance is 50. The tracker did not update correctly when the forced transfer moved tokens out of her wallet. As a result, the system thinks she holds more than she actually does — which could allow her to receive more tokens than the cap allows in a future transaction. Only one test failed out of the 20 run.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* 5  
> *Note:* This is the most precisely diagnosed report. The affected function is identified exactly: `token.forcedTransfer`. The suggested fix is specific and actionable: "check how forcedTransfer updates the MaxBalanceModule's tracked balance for the sender's identity, and make it match the real balance change." A developer reading this knows exactly which function to inspect.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* 5  
> *Note:* The reproduction steps are a perfect four-step sequence: mint, burn (which passes), forced transfer (which fails), then the exact assertion failure is shown — "idA tracked != real: 75 != 50." The numbers are concrete and verifiable. The Solidity test code matches the steps exactly. The fact that the burn passed and only the forced transfer failed is a meaningful narrowing of the bug scope, and the report captures this.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 5  
> *Note:* The clearest of the problem reports. One rule fails, one test fails, the failure value is precise (75 vs 50), the affected function is named, and the remaining tests passing is noted ("The check after the burn passed, so the burn appears correct"). The only minor ambiguity is "the output reports only idA, so the other identities were not shown to fail" — a thorough reader might ask whether other identities could also be affected. This is an honest limitation, not a flaw in clarity.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 5  
> *Note:* The report delivers a clear narrative: forced transfers do not update the balance tracker. Fix: make forcedTransfer update the tracker to match the real balance change. The function to fix is named. The test to rerun is named. A responsible party can send this report directly to a developer with no additional explanation needed.

---

## Optional Deep-Dive

### A. Triage labels (`results/review_triage.md`)

> I read the per-run table and the label descriptions.
>
> **Stock gap labels (S03/S04):** The label is correct. S03 and S04 are known, documented vulnerabilities in the ONCHAINID dependency (revoked claims revivable via signature manipulation). They are reproduced by existing tests in `StockGaps.t.sol` and `StockGapsVByte.t.sol`. Flagging these on clean configurations is not a false alarm in the strict sense — the finding is real — but it is also not caused by any seeded variant. The label "stock gap" rather than "false alarm" is a fair and transparent choice.
>
> **C08 label ("Real"):** The document acknowledges this is contested. `review_triage.md` calls it a real finding (pre-binding mint to Carol in a restricted country), while `Phase3.md` §6 treats the pre-binding setup as a legal step and calls flagging it a false alarm. Both readings are defensible. I would note this as an *open classification question* rather than label it definitively either way. The report already does this, which is appropriate.
>
> **False alarm (missing input):** Labelling the J3 "token not bound" finding as a false alarm caused by missing input is correct. The token binding happens in `Token.init` → `setCompliance`, which was not shown to the reviewer in r1/r1b. The model's error is a consequence of incomplete context, not a hallucination. The fix (expanded code view in r2) eliminated the false alarm, which confirms the diagnosis.
>
> **Overall:** I agree with all three label categories. The table is honest about its limits (team-authored, only three runs per model, Sonnet has no variance range). No labels would I change.

### B. Generated test alignment (V04 — `test_mintToUnverifiedWalletReverts`)

> Rule K1 says: *"Only investors with a valid KYC claim from a trusted issuer may receive tokens."*
>
> The test `test_mintToUnverifiedWalletReverts` does check the core of K1: it attempts to mint to Mallory (who has no KYC claim) and asserts the transaction reverts with "Identity is not verified." If the revert happens, we know the KYC gate blocked the mint. This is correct and well-targeted.
>
> **What the test does not check:** K1 specifies the claim must come from a *trusted issuer*. The test checks that an investor with *no claim at all* is blocked, but does not check whether an investor with a claim from an *untrusted issuer* is also blocked. These are different conditions. A configuration could pass this test while still letting investors with claims from non-whitelisted issuers receive tokens. This is a known gap in coverage (not in this test alone, but in the generated suite as a whole for this scenario). It is worth noting that the test is still a valid and meaningful check for the most common failure mode.

### C. Explanation accuracy (V12 — H3 "What went wrong" paragraph)

> The paragraph says: *"After the forced transfer, Alice's tracked balance is 75 but her real balance across both wallets is 50. The tracker did not drop when the tokens left her wallet. The check after the burn passed, so the burn appears correct."*
>
> The reproduction steps confirm all of this:
> - 100 tokens minted to a1; tracker checked → passes (implicit: tracker is 100 at this point).
> - 25 tokens burned; tracker checked → passes (tracker drops to 75, real is 75 — consistent).
> - 25 tokens forced-transferred from a1 to b; tracker checked → **fails**: tracker still 75, real is 50.
>
> The numbers add up: 100 − 25 (burn) − 25 (forced transfer) = 50 real, but tracker stayed at 75 after the burn and was not updated by the forced transfer. The explanation matches the steps exactly.
>
> One small observation: the paragraph says "real balance across both wallets is 50" — but the test only interacted with a1, not a2. This is accurate because a2 holds 0 tokens throughout, so the total across both wallets is indeed 50. A reader with no prior context might wonder why "both wallets" is mentioned if only one was used. A note such as "Alice's second wallet a2 holds no tokens throughout" would remove any ambiguity. This is not an inaccuracy, just a minor clarity point.

---

## Results Summary

| Report | Q1 (problem found?) | Q2 Fix clarity | Q3 Evidence | Q4 Clarity | Q5 Actionable | Key feedback |
|---|---|---|---|---|---|---|
| Report A (C01) | No problem — all clean | N/A | N/A | 5/5 | 5/5 | "forcedTransfer" needs a one-line gloss for non-technical readers |
| Report B (V04) | Yes — KYC bypassed, side-effect H3 correctly identified | 4/5 | 5/5 | 4/5 | 4/5 | "direct evidence: 0 of 1" is counterintuitive; "idA" needs introduction |
| Report C (V05) | Yes — country restriction not enforced | 4/5 | 5/5 | 5/5 | 4/5 | Clearest failing report; cap reference in steps is a minor distraction |
| Report D (V09) | Yes — cap and tracker both broken | 4/5 | 5/5 | 4/5 | 4/5 | Symptom hint is excellent; "0 != 500" needs a lay explanation |
| Report E (V12) | Yes — forced transfer skips tracker | 5/5 | 5/5 | 5/5 | 5/5 | Most precisely diagnosed report; "both wallets" note minor ambiguity |

**Average scores (Q2–Q3 for failing reports B–E; Q4–Q5 across all five):**

| Question | Average |
|---|---|
| Q2 Fix clarity (reports B–E) | **4.25 / 5** |
| Q3 Evidence (reports B–E) | **5.00 / 5** |
| Q4 Report clarity (all five) | **4.60 / 5** |
| Q5 Actionability (all five) | **4.40 / 5** |

---

## Summary of Main Findings

1. **Evidence quality is high.** All four failing reports provide numbered reproduction steps, exact assertion failure messages, and inline Solidity test code. An evaluator can verify every claim without running the tool. Q3 averaged 5/5.

2. **Fix clarity is good but not perfect.** Reports correctly identify which functions to inspect and in three cases (V05, V09, V12) provide a specific actionable fix suggestion. The main gap is that the exact configuration value that is wrong is usually not stated — the report says "compare with C01" or "check the module list." For a non-technical token issuer this requires a developer intermediary. Q2 averaged 4.25/5.

3. **Side-effect handling works.** Report B (V04) correctly identifies the H3 failure as a side effect of the K1/K3 failure, writes "direct evidence: 0 of 1 failing tests," and adds the note "All failing H3 tests are side effects of the KYC failure above. No separate holding-limit problem is shown." This is exactly right and prevents a reader from chasing a second root cause that does not exist.

4. **Language occasionally assumes technical context.** Terms like "idA," "forcedTransfer," "CAP," "direct_evidence.direct == 0," and "identity balance" appear without definition. A glossary or inline parenthetical would bring Report A and Report D up to 5/5 on clarity.

5. **Report E (V12) is the best-written failing report.** One rule, one test, concrete numbers, named function, specific fix. If the format were guided by any template, V12's report would be the model to follow.

6. **The triage labels are consistent and defensible.** The stock-gap / real / false-alarm categorisation is correct. The C08 open question is handled transparently. The evaluator would not change any label.

7. **Generated test coverage has a known gap.** The K1 test checks for investors with no claim at all, but does not cover investors with claims from untrusted issuers. This is a coverage observation, not a report quality issue.

---

## Limitations of This Evaluation

1. **No baseline for calibration.** Poorvi has not previously read compliance audit reports for token systems, so scores reflect first-impression clarity rather than a comparison against an industry standard.
2. **Single-pass read.** The evaluation was conducted in one sitting without the opportunity to ask the tool authors clarifying questions during the session.
3. **Domain terminology.** Some smart contract terms (forcedTransfer, CAP, identity balance) were unfamiliar. Where terminology was unclear, it was noted in the per-report feedback rather than assumed.
