# Triage of clean-target findings, all LLM-only review runs (step 4.8)

Runs: r1 (official), r1b (repeat of r1, same input, `--sample 1`), r2 (code view also shows `Token.init`, `setCompliance`, `setIdentityRegistry`, `bindToken`, `getTokenBound`). Models: Haiku 5.5 and Sonnet 5.5.
Where a run needed a retry for invalid JSON, the view with the retry answers is used.

Made by the project team after seeing the answers, by reading each finding against the code the reviewer was shown. It replaces `results/review_r1_haiku/triage.md`, which covered r1 only. The official numbers in each `report.md` are not changed by this file. An independent evaluator (Phase 5) should check these labels.

## Labels

| Label | Meaning |
|---|---|
| Stock gap (S03/S04) | A K2 finding about revoked claims being revived through a different signature byte string. S03 (twin signature) and S04 (v byte written as 0 or 1) are both reproduced by tests (`StockGaps.t.sol`, `StockGapsVByte.t.sol`). A real gap of the ONCHAINID dependency, not a seeded variant |
| Real (C08) | J1 on C08. The C08 start state mints 300 tokens to Carol (country 408) before any module is bound, so a restricted-country wallet holds tokens. The gold tests only judge calls made after setup, so they never counted it |
| False alarm (missing input) | J3 "the setup never binds the token". `Token.init` calls `setCompliance`, which binds the token. In r1 and r1b the reviewer was not shown that code. In r1b the model wrote that whether a bind step exists in code not shown could not be verified |

## Per run

| Run | Stock gap on | Real (C08) | False alarm | Frozen | Adjusted | After triage |
|---|---|---|---|---|---|---|
| Haiku r1 | C01 C02 C03 C06 C07 | C08 | C04 | 7 of 8 | 2 of 8 | 1 of 8 |
| Haiku r1b | C01 C03 C05 C07 | none | C02 | 5 of 8 | 1 of 8 | 1 of 8 |
| Haiku r2 (+retry) | C02 C03 C04 | C08 | none | 4 of 8 | 1 of 8 | 0 of 8 |
| Sonnet r1 (+retry) | none | C08 | none | 1 of 8 | 1 of 8 | 0 of 8 |
| Sonnet r1b (+retry) | none | C08 | none | 1 of 8 | 1 of 8 | 0 of 8 |
| Sonnet r2 (+retry) | C06 | none | none | 1 of 8 | 0 of 8 | 0 of 8 |

Frozen = any HIGH or MEDIUM finding on a clean target. Adjusted = frozen, ignoring stock-gap findings (scorer word list). After triage = true false alarms only.

## False-positive ranges to quote (same-input runs r1 and r1b)

| Model | Frozen | Adjusted | After triage | After triage, r2 code view |
|---|---|---|---|---|
| Haiku | 5 to 7 of 8 (63% to 88%) | 1 to 2 of 8 (13% to 25%) | 1 of 8 (13%) in both runs | 0 of 8 |
| Sonnet | 1 of 8 (13%) in both runs | 1 of 8 (13%) in both runs | 0 of 8 (0%) in both runs | 0 of 8 |

## Observations

1. The token-binding false alarm happened only with Haiku, on a different target each time (C04 in r1, C02 in r1b), and did not appear in r2. It comes from missing input, so the fix is in the code view, not in the prompt. The r2 code view is the better view for any later use.
2. C08 was reported in 4 of 6 runs (Haiku r1 and r2, Sonnet r1 and r1b) and missed in 2 (Haiku r1b, Sonnet r2). The finding is real and comes from the design of C08, not from a model error. C08 is documented, not changed, so the Phase 3 and 4 numbers stay valid.
3. The S03/S04 family: Haiku reported it in all three runs, on 3 to 5 clean targets each time. Sonnet reported it once in three runs (C06 in r2). No generated test targets it.
4. Limits: the labels are one team's reading after seeing the output. There are only three runs per model, and Sonnet has no run-to-run range beyond r1 and r1b.