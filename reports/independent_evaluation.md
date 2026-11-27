# ComplyRWA — Independent Evaluation Record

**Evaluation date:** 2026-11-27  
**Branch:** `charvi-reports`  
**Recorded by:** Member 3 (Charvi)

---

## Evaluator Profile

| Field | Details |
|---|---|
| **Name** | Poorvi (named with permission) |
| **Role** | Independent reviewer — outside the project team |
| **Background** | General software and review background; no prior knowledge of the ComplyRWA codebase, the seeded variants, or the benchmark results |
| **Relationship to team** | Outside the team (independent) |

---

## Reports Evaluated

| Blinded Label | Source file | Target (revealed after review) |
|---|---|---|
| Report A | `results/demo_C01/report.md` | C01 — baseline, all rules clean |
| Report B | `results/demo_V04/report.md` | V04 — KYC topics list emptied |
| Report C | `results/demo_V05/report.md` | V05 — wrong country restricted |
| Report D | `results/demo_V09/report.md` | V09 — MaxBalanceModule removed |
| Report E | `results/demo_V12/report.md` | V12 — forcedTransfer skips tracker |

> *Poorvi read the five reports in blinded order (Report A through Report E) without being told in advance which ones had bugs.*

---

## Questionnaire Responses

**Scale:** 1 = not at all / completely unclear / not actionable · 5 = completely clear / very actionable

---

### Report A (C01 — clean)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Everything looks fine. All 20 tests passed across the 5 rules, and there are no findings. There is one INFO note at the bottom saying the country rule can be bypassed via `forcedTransfer`, but it says that's a known exception and not a bug.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* N/A — no problem found  
> *Note:* Nothing to fix here.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* N/A — no failing tests  
> *Note:* The table shows 4/4 passed for each rule, which is enough for a clean report.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 5  
> *Note:* Very easy to read. The only minor thing is `forcedTransfer (agent-only path)` in Section 4 — if I weren't technical, I wouldn't immediately know what `forcedTransfer` means, so a short plain-English note (like "admin override") would help.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 5  
> *Note:* Clear green light — no findings, and the one exception is explained as expected behaviour.

---

### Report B (V04 — KYC bypassed)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Yes, there's a KYC problem. Someone without a KYC claim (Mallory) was able to receive tokens through both minting and transfers, and someone whose KYC claim was revoked (Bob) could still receive tokens too. Three rules failed (K1, K3, and H3), though under H3 it says that failure is just a side effect of the KYC issue rather than a separate holding-limit bug. The report says it can't tell the exact cause from the output alone and suggests comparing this setup with the clean baseline (C01).

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* 4  
> *Note:* It tells a developer where to look (`token.mint`, `token.transfer`, and adding the KYC claim topic with `ctr.addClaimTopic`), which is helpful. Not a 5 because it doesn't pinpoint which exact setting is wrong — someone still has to compare it against C01 to find it.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* 5  
> *Note:* Yes. It lists the exact steps (mint 1 token to Mallory, expected it to fail, it went through instead) and shows all three failing tests. Calling out H3 as a side effect is also really helpful so you don't waste time looking for a second bug.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 4  
> *Note:* Mostly clear, and grouping by rule helps. Two small things confused me: it uses `idA` without saying what that stands for, and `Direct evidence: 0 of 1 failing tests` under H3 sounds weird at first until you read the next line saying it's a side effect.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 4  
> *Note:* I know KYC is broken and which functions to hand off to a developer to check, though they'll still have to dig into the config to find the exact setting.

---

### Report C (V05 — wrong country restricted)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Yes, the country restriction isn't blocking restricted investors. Minting, `transfer`, and `transferFrom` all went through for Bob even after he was put in a restricted country. KYC passed, so it's just the jurisdiction rule that's broken. The report suggests checking that the country module is attached and that the restricted country setting is right.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* 4  
> *Note:* Clear enough for a developer — check the country restriction module binding and the restricted-country setting. Not a 5 because it doesn't say which country code is currently set vs. what it should be.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* 5  
> *Note:* Very convincing. It shows the steps clearly (set Bob's country to restricted, try to mint, expected `"Compliance not followed"`, didn't fail) and covers all three ways tokens can be sent.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 5  
> *Note:* Easiest to follow of the failing reports. Only tiny thing is step 3 mentioning "V05's cap is not given" when this test is about countries, not caps — made me wonder for a second if the cap mattered.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 4  
> *Note:* Tells me what's broken and which module to check; just needs someone to look up the intended country code from our policy.

---

### Report D (V09 — holding limit removed)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Yes, the holding limit isn't working at all. Bob was able to get minted more tokens than the cap allows, and the module's tracked balance stays at 0 even after tokens are minted (0 instead of 100). Because it stays at 0, the cap check never triggers. At the bottom there's a helpful hint saying the module probably isn't being notified and to check if `MaxBalanceModule` is even listed in `compliance.getModules()`.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* 4  
> *Note:* The hint to check `compliance.getModules()` for `MaxBalanceModule` makes it pretty clear what a developer should check first. Scored 4 instead of 5 because it notes the cap value itself isn't in the inputs, so that still has to be verified separately.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* 5  
> *Note:* Yes — all 4 tests failed on H1 and all 4 failed on H3, and the `0 != 100` numbers make it obvious the counter isn't updating at all.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 4  
> *Note:* Good overall, and the symptom hint under H3 is great. The `0 != 500` error on two of the H1 tests is a bit cryptic at first, though the "(side effect: the module's counter did not move)" note helps explain it.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 4  
> *Note:* Very clear what to tell the dev team: the holding-limit module isn't tracking balances or enforcing the cap, check if it's even connected.

---

### Report E (V12 — forcedTransfer skips tracker)

**Q1. In your own words, what does this report say? Is there a problem, and if so what?**

> Yes, there's a specific bug with `forcedTransfer`. Normal minting, transfers, and burns all pass, so the holding limit mostly works. But after a `forcedTransfer` moves tokens out of Alice's wallet, her tracked balance stays at 75 while her real balance is 50. So the tracker forgot to subtract the tokens from the sender on a forced transfer.

**Q2. If there is a problem, do you understand what should be fixed and roughly who should fix it?**

> *Score:* 5  
> *Note:* Super clear. It points straight to `token.forcedTransfer` and says to check how it updates `MaxBalanceModule`'s tracked balance for the sender.

**Q3. Is the evidence given (test results, reproduction steps) convincing?**

> *Score:* 5  
> *Note:* Yes, the 4 steps make it obvious: mint 100, burn 25 (passes), forced-transfer 25 (fails with 75 vs 50). Seeing the burn pass right before it narrows it down nicely.

**Q4. How clear is this report? Is anything confusing or unclear?**

> *Score:* 5  
> *Note:* Very clear and to the point. Only minor thing is it mentions "her real balance across both wallets is 50" even though the steps only mention `a1`, so I had to assume the second wallet was empty.

**Q5. How actionable is this report for you as the person responsible for this token?**

> *Score:* 5  
> *Note:* Can hand this straight to a developer — exact function, exact numbers, and exact test to re-run.

---

## Optional Deep-Dive

### A. Triage labels (`results/review_triage.md`)

> I looked through the table and label notes. Calling the signature-trick findings "stock gaps" makes sense since the note explains they're real issues in the underlying dependency rather than bugs added by the test configs. Same for the missing-input false alarms — if the model wasn't shown the binding code, it's fair to note that as missing input. The C08 one is a bit grey since the team itself notes a disagreement on whether pre-setup tokens should count, so keeping that flagged for discussion makes sense. I wouldn't change the labels.

### B. Generated test alignment (V04 — `test_mintToUnverifiedWalletReverts`)

> The rule says investors need a valid KYC claim *from a trusted issuer*. Looking at the test, it checks that minting to Mallory (who has no claim at all) fails. That makes sense for the basic case, but it doesn't seem to test what happens if someone has a claim from an *untrusted* issuer — so that part of the rule isn't really checked by this test.

### C. Explanation accuracy (V12 — H3 "What went wrong" paragraph)

> Yes, the numbers match the steps: start with 100, burn 25 (down to 75, check passes), then forced-transfer 25 (real balance drops to 50, tracker stays at 75). Everything in the paragraph matches the steps, except saying "across both wallets" when only `a1` is mentioned in the steps (assuming her other wallet is just 0).

---

## Results Summary

| Report | Q1 (problem found?) | Q2 Fix clarity | Q3 Evidence | Q4 Clarity | Q5 Actionable | Key feedback |
|---|---|---|---|---|---|---|
| Report A (C01) | No problem — all clean | N/A | N/A | 5/5 | 5/5 | `forcedTransfer` needs a one-line gloss for non-technical readers |
| Report B (V04) | Yes — KYC bypassed; side-effect H3 correctly identified | 4/5 | 5/5 | 4/5 | 4/5 | `direct evidence: 0 of 1` is counterintuitive; `idA` needs introduction |
| Report C (V05) | Yes — country restriction not enforced | 4/5 | 5/5 | 5/5 | 4/5 | Clearest failing report; cap reference in steps minor distraction |
| Report D (V09) | Yes — cap and tracker both broken | 4/5 | 5/5 | 4/5 | 4/5 | Symptom hint excellent; `0 != 500` needs lay explanation |
| Report E (V12) | Yes — forced transfer skips tracker | 5/5 | 5/5 | 5/5 | 5/5 | Most precisely diagnosed report; "both wallets" note minor |

**Average scores (Q2–Q3 for failing reports B–E; Q4–Q5 across all five):**

| Question | Average |
|---|---|
| Q2 Fix clarity (reports B–E) | **4.25 / 5** |
| Q3 Evidence (reports B–E) | **5.00 / 5** |
| Q4 Report clarity (all five) | **4.60 / 5** |
| Q5 Actionability (all five) | **4.40 / 5** |

---

## Summary of Main Findings

1. **Evidence is easy to follow:** The numbered steps and concrete numbers (`0 != 100`, `75 != 50`) make it clear something is actually broken even without reading the Solidity code (Q3 = 5.0/5).
2. **Fixes point to the right area, though a developer is still needed:** The reports name the functions and modules to check, which is helpful, though for most config bugs you still need a developer to look up the exact setting (Q2 = 4.25/5).
3. **Side-effect notes help:** Flagging H3 as a side effect in Report B stops a reader from chasing a second problem that isn't there.
4. **Some jargon isn't explained:** Terms like `forcedTransfer`, `idA`, `CAP`, and `Direct evidence: 0 of 1` would be clearer with a brief plain-English note.
5. **Report E (V12) was the clearest failing report:** One rule, one failing test, exact function (`forcedTransfer`), and exact numbers.

---

## Limitations of This Evaluation

1. **No baseline for comparison:** Poorvi has not previously reviewed compliance audit reports for token systems, so scores reflect first-impression clarity rather than an industry benchmark.
2. **Single-pass review:** Done in one sitting without a live Q&A session with the authors.
3. **Technical terms:** A few smart-contract terms (`forcedTransfer`, `CAP`, `idA`) were unfamiliar and noted in the clarity feedback.
