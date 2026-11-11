| contract | test | outcome | reason | notes |
|---|---|---|---|---|
| BadTests | test_BAD1_failsEverywhere | REJECT | fails on clean: C01 C02 C05 C06 C08 (always fails) | ran on 5/8 clean, 12/13 variants |
| BadTests | test_BAD2_noAssertion | VACUOUS | passes on all 12 variants it ran on | no visible assertion; ran on 5/8 clean, 12/13 variants |
| BadTests | test_BAD3_alwaysTrue | VACUOUS | passes on all 12 variants it ran on | ran on 5/8 clean, 12/13 variants |
| BadCompile | (whole contract) | REJECT | does not compile | Error: Compiler run failed: | Error (7576): Undeclared identifier. |   --> candidates/bad/BadCompile.sol:10:9: |    | | 10 |         thisFunctionDoesNotExist(); |    |         ^^^^^^^^^^^^^^^^^^^^^^^^ |
