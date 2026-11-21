# LLM-only review: review_mock_r1_haiku

| measure | value |
|---|---|
| variants detected (official) | 1 of 13 = 8% |
| variants detected (strict, names the changed code) | 1 of 13 = 8% |
| variants with any HIGH/MEDIUM finding | 13 of 13 |
| clean targets with a false positive | 8 of 8 = 100% |
| false-positive findings on a rule outside the 10 listed | 0 |
| targets with no valid answer | 0 (none) |
| LLM calls (cut off) | 21 (0) |
| input / output tokens | 215,812 / 1,911 |
| cost USD | $0.0225 |
| model time (seconds) | 0 |

## Variants

| target | status | official | strict | rules flagged (HIGH/MEDIUM) | matched finding |
|---|---|---|---|---|---|
| V01 | ok | no | no | K3 |  |
| V02 | ok | no | no | K3 |  |
| V03 | ok | no | no | K3 |  |
| V04 | ok | yes | yes | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |
| V05 | ok | no | no | K3 |  |
| V06 | ok | no | no | K3 |  |
| V07 | ok | no | no | K3 |  |
| V08 | ok | no | no | K3 |  |
| V09 | ok | no | no | K3 |  |
| V10 | ok | no | no | K3 |  |
| V11 | ok | no | no | K3 |  |
| V12 | ok | no | no | K3 |  |
| V13 | ok | no | no | K3 |  |

## Clean targets

| target | status | false positive | rules flagged (HIGH/MEDIUM) | first serious finding |
|---|---|---|---|---|
| C01 | ok | YES | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |
| C02 | ok | YES | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |
| C03 | ok | YES | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |
| C04 | ok | YES | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |
| C05 | ok | YES | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |
| C06 | ok | YES | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |
| C07 | ok | YES | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |
| C08 | ok | YES | K3 | K3 HIGH: ClaimTopicsRegistry.removeClaimTopic / setup _deployClaimIss |

## How to read this

- The reviewer reads the code and setup of each target and lists rule breaks without running anything.
- Official detection needs a HIGH or MEDIUM finding on a linked rule. Strict detection also needs a word that names the changed code.
- A clean target with any HIGH or MEDIUM finding counts as a false positive.
- An empty, cut-off or invalid answer is never counted as 'no findings'.
