# Three-way benchmark (project step 4.8)

| Method | Variants detected (of 13) | False alarms on the 8 clean configurations | Tokens in / out | Cost USD | Time (s) |
|---|---|---|---|---|---|
| Hand-written Foundry tests (no LLM) | 13/13 | 0 of 8 | 0 / 0 | $0 | 88 (Foundry run incl. compile) |
| LLM-generated tests, Haiku | 12/13 | 0 of 8 configurations (0 of 40 tests rejected for failing on a clean configuration) | 88,231 / 52,594 | $0.0351 | 407 (236 model + 171 Foundry) |
| LLM-generated tests, Sonnet | 12/13 | 0 of 8 configurations (0 of 40 tests rejected for failing on a clean configuration) | 80,278 / 22,454 | $0.3851 | 297 (163 model + 134 Foundry) |
| LLM-only review, Haiku (r1; repeat r1b) | 13/13; r1b: 13/13 | frozen / adjusted / after triage: r1 7 / 2 / 1; r1b 5 / 1 / 1 | r1 335,658 / 85,812 | r1 $0.0765; r1b $0.0766 | r1 797; r1b 401 (model time) |
| LLM-only review, Sonnet (r1; repeat r1b) | 13/13 after retry (12/13 as first answered); r1b: 13/13 after retry (11/13 as first answered) | frozen / adjusted / after triage: r1 1 / 1 / 0; r1b 1 / 1 / 0 | r1 351,617 / 25,664 | r1 $0.9599; r1b $0.9973 | r1 244; r1b 236 (model time) |

## Which variants each method catches

| Variant | Hand-written | Generated Haiku | Generated Sonnet | Review Haiku (r1) | Review Sonnet (r1, after retry) |
|---|---|---|---|---|---|
| V01 | yes | yes | yes | yes | yes |
| V02 | yes | yes | yes | yes | yes |
| V03 | yes | yes | yes | yes | yes |
| V04 | yes | yes | yes | yes | yes |
| V05 | yes | yes | yes | yes | yes |
| V06 | yes | yes | yes | yes | yes |
| V07 | yes | yes | yes | yes | yes |
| V08 | yes | yes | yes | yes | yes |
| V09 | yes | yes | yes | yes | yes |
| V10 | yes | yes | yes | yes | yes |
| V11 | yes | NO | NO | yes | yes |
| V12 | yes | yes | yes | yes | yes |
| V13 | yes | yes | yes | yes | yes |

## How to read this

- Detected: a variant counts when the method reports or fails on it. Hand-written and generated tests: a linked or any test fails on the variant while passing on every clean configuration. Review: a HIGH or MEDIUM finding on a linked rule.
- False alarms: tests are judged on the clean configurations (a generated test that fails there is rejected). The review is judged by its HIGH and MEDIUM findings on clean configurations: frozen = as defined before the runs, adjusted = ignoring the stock gaps S03/S04, after triage = true false alarms only (manual labels, see review_triage.md). The three-count form is frozen / adjusted / after triage.
- The methods see different things. The hand-written tests are the answer key, written by the same author as the variants. The generated tests see only the clean pinned code and the policy text, never the variants. The review sees each target's own code and setup, with comments removed, so it is easier than blind testing. Seven variants are configuration-only changes (V04, V05, V07, V08, V09, V11, V13), where the setup override shows the change itself. Four variants (V03, V06, V10, V12) are visible only in the code, with no setup override.
- Time: model time is the sum of the API call times. Foundry time is the executor run on all configurations including compile. The time to write the hand-written tests and the variants by a person is not counted.
- Costs of the generated tests cover generation only. The explainer adds about $0.0014 per finding on Haiku (Phase 4.6).
- Review rows: Sonnet's first answer was invalid JSON for some targets. One retry per invalid answer was allowed for both models; the cost and time of the retries are included.
- Each review number comes from one run per batch. The two runs on the same input (r1 and r1b) show the run-to-run range.
