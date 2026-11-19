| measure | Haiku | Sonnet |
|---|---|---|
| model | claude-haiku-5-5 | claude-sonnet-5-5 |
| rules covered | 10 (H1 H2 H3 H4 J1 J2 J3 K1 K2 K3) | 10 (H1 H2 H3 H4 J1 J2 J3 K1 K2 K3) |
| tests judged | 40 | 40 |
| KEEP / VACUOUS / REJECT | 32 / 8 / 0 | 32 / 8 / 0 |
| valid and non-vacuous (KEEP) | 80% | 80% |
| variants killed by a generated test | 12 of 13 (missing: V11) | 12 of 13 (missing: V11) |
| LLM calls (failed = cut off) | 11 (1 failed) | 10 (0 failed) |
| input tokens | 88,231 | 80,278 |
| output tokens | 52,594 | 22,454 |
| cost USD (all calls incl. failed) | $0.0351 | $0.3851 |
| cost USD per rule | $0.0035 | $0.0385 |
| model time (seconds, all calls) | 236 | 163 |
