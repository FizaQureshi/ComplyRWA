# Manual triage: clean targets flagged by the Haiku review (batch r1)

Made after seeing the answers, by reading each finding against the pinned code that the reviewer was shown.
The official numbers in `report.md` are not changed by this file. An independent evaluator (Phase 5) should check these labels.

Clean targets with a HIGH or MEDIUM finding: 7 of 8 as frozen. 3 of 8 after ignoring the twin-signature gap (S03) by the scorer's word list.

| Target | Finding | Label | Reason |
|---|---|---|---|
| C01, C03, C06, C07 | K2: revoked claim re-added with the twin signature (r, n-s, v^1) | Real stock gap (S03) | Same gap reproduced in `StockGaps.t.sol`. Ignored by the adjusted score |
| C02 | K2: revoked claim re-added after changing the v byte from 27/28 to 0/1 | Real stock gap, same family as S03 (not yet reproduced by a test) | `getRecoveredAddress` adds 27 when v is below 27, so a different v byte recovers the same signer, and revocation is keyed on the exact signature bytes. The scorer's word list did not match this wording |
| C04 | J3 MEDIUM: setup never calls `bindToken`, so the compliance contract has no token | False alarm, caused by missing input | `Token.init` calls `setCompliance`, which binds the token. The reviewer's code view did not include `Token.init` or `setCompliance`, so it could not see this |
| C08 | J1 HIGH: 300 tokens are minted to Carol (country 408) before the country module is bound | Real, caused by the design of C08 | The C08 start state mints before any module is bound, so a restricted-country wallet holds tokens. The gold tests only judge calls made after setup, so they never counted it |

Result after triage: 1 false alarm among 8 clean targets (12.5%). Two findings are real weaknesses (C02, C08) and five targets show the S03 family.

Follow-ups, none done yet:
1. Write a Foundry test for the v-byte route (a possible S04) before calling it a confirmed gap.
2. Decide how to document C08: its start state is not clean for the literal J1 rule.
3. Consider a second batch (r2) whose code view also includes `Token.init` and `setCompliance`, for both models.