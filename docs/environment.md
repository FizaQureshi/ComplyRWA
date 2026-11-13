# ComplyRWA: Environment Record

Phase 0 reproducibility record. Every benchmark result in this project depends on these versions, so update this file whenever any of them change.

Last updated: 2026-11-13

---

## 1. Host machine

| Item | Value |
|---|---|
| Operating system | Windows (native, no WSL) |
| Shells used | Git Bash (Git, Node, Foundry, T-REX), PowerShell (Halmos venv) |
| Editor / repo tools | VS Code, GitHub Desktop |

## 2. Tool versions

| Tool | Version | How to check |
|---|---|---|
| Git | 2.37.3.windows.1 | `git --version` |
| Node.js | 20.20.2 (LTS, via nvm-windows) | `node -v` |
| npm | 10.8.2 (run `npm -v` under Node 20) | `npm -v` |
| Python (Halmos venv) | 3.11.9 | `python --version` (venv active) |
| Foundry (`forge`) | 1.8.7 | `forge --version` |
| Halmos | 0.3.3 | `halmos --version` |
| Hardhat | 2.14.0 (from `T-REX/package.json`) | `npx hardhat --version` |
| fuzz seed | 0x436f6d706c79 | invariant runs 64 | depth 40 |
| ONCHAINID (`@onchain-id/solidity`) | 2.1.0 | `grep '"version"' T-REX/node_modules/@onchain-id/solidity/package.json` |

### Foundry build details

```
forge Version: 1.8.7
Commit SHA: 985eeea031d79922cd654d4e94e6c3701e1c7d73
Build Timestamp: 2026-10-29T14:56:59Z
Build Profile: dist
```

### Halmos install notes

- Installed in an isolated venv at `%USERPROFILE%\.venvs\halmos`, created with Python 3.11.9.
- Activate with: `& "$HOME\.venvs\halmos\Scripts\Activate.ps1"`
- **Non-standard install.** The default `pip install halmos` failed because `safe-pysha3` needs a C++ compiler. Workaround used:
  1. `pip install halmos --no-deps`
  2. Installed the dependencies by hand, using the `eth_hash[pycryptodome]` hashing backend instead of `safe-pysha3`.
- Solvers: `z3-solver` 4.12.6.0 and `yices-solver` 2.6.4 (installed as Halmos dependencies).
- Halmos calls `forge`, so Foundry's `bin` folder must be on PATH in the shell where Halmos runs (`C:\Users\fizaq\.foundry\bin`).

## 3. Pinned target system: T-REX (ERC-3643)

| Item | Value |
|---|---|
| Repository | https://github.com/TokenySolutions/T-REX |
| Pinned tag | `4.1.6` (newest non-beta tag at pinning time) |
| Commit hash | **a09cfd38aa257d56db7ff9c90f30e65f125a141b** (run `git rev-parse HEAD` inside `T-REX/`) |
| Cloned into | `ComplyRWA/T-REX/` (git-ignored by this repo, left unmodified) |
| Solidity compiler | 0.8.17 |
| Optimizer | enabled, 200 runs |
| Key dependencies | `@openzeppelin/contracts`, `@openzeppelin/contracts-upgradeable`, `@onchain-id/solidity` |

Contract folders under `T-REX/contracts/`: `token`, `registry`, `compliance`, `factory`, `proxy`, `roles`, `DVA`, `DVD`, `_testContracts`.

## 4. Baseline results

### Hardhat (T-REX's own test suite)

Commands: `npm ci`, `npx hardhat compile`, `npx hardhat test`

| Metric | Result |
|---|---|
| Passing | 777 |
| Failing | 0 |
| Total time | about 1 minute |

### Foundry build

Command: `forge build` (run from the repo root, using `foundry.toml`)

| Metric | Result |
|---|---|
| Outcome | Compiler run successful |
| Warning origin | All from T-REX sources and libraries, not modified |

### Halmos smoke test

Project: `D:\IIT-DELHI-INTERN-Cerify\smoke` (separate throwaway folder)
Test: `check_add_commutes(uint256 a, uint256 b)` asserts `a + b == b + a` in an `unchecked` block.

| Metric | Result |
|---|---|
| Result | `[PASS]`, 1 path |
| Time | 0.02 s |
| Compiler Foundry auto-installed | Solc 0.8.38 (smoke project only) |

## 5. Foundry configuration

`foundry.toml` lives in the repo root, not inside `T-REX/`, so the pinned code stays untouched.

```toml
[profile.default]
src = "T-REX/contracts"
test = "test"
out = "out"
libs = ["T-REX/node_modules"]
solc_version = "0.8.17"
evm_version = "london"
optimizer = true
optimizer_runs = 200
remappings = [
  "@openzeppelin/=T-REX/node_modules/@openzeppelin/",
  "@onchain-id/=T-REX/node_modules/@onchain-id/",
]
```

Settings mirror `T-REX/hardhat.config.ts` (Solidity 0.8.17, optimizer 200 runs) so both tools produce comparable bytecode.

## 6. How to reproduce from scratch

1. Install Git for Windows, Node 20 LTS, Python 3.11, VS Code.
2. Install Foundry: in Git Bash, `curl -L https://foundry.paradigm.xyz | bash`, then `foundryup`. Add `~/.foundry/bin` to PATH.
3. Create the Halmos venv with Python 3.11 and install Halmos (see section 2 notes).
4. `git clone https://github.com/TokenySolutions/T-REX.git`, then `git checkout tags/4.1.6`.
5. Inside `T-REX/`: `npm ci`, `npx hardhat compile`, `npx hardhat test` (expect 777 passing).
6. From the repo root with `foundry.toml` in place: `forge build`.

## 7. Problems and fixes log

| # | Problem | Cause | Fix |
|---|---|---|---|
| 1 | `forge: command not found` after install | Installer does not update PATH in the open Git Bash session | `export PATH="$PATH:/c/Users/fizaq/.foundry/bin"`, then `foundryup`; add the line to `~/.bashrc` for persistence |
| 2 | `echo ... >> ~/.bashrc` gave `command not found` | Invisible character pasted in front of the command | Retype the command, or paste with Shift+Insert and check the line first |
| 3 | `Ctrl+V` does not paste in Git Bash | Git Bash uses different shortcuts | Use Shift+Insert, right-click, or enable Ctrl+Shift+letter shortcuts in Options |
| 4 | Node 25.2.1 installed | "Current" release, not LTS; Hardhat expects LTS | Installed Node 20 LTS via nvm-windows (20.20.2) |
| 5 | `$HOME\...\Activate.ps1` parse error in PowerShell | A path starting with a variable is parsed as an expression | Call with `&` and quotes: `& "$HOME\.venvs\halmos\Scripts\Activate.ps1"` |
| 6 | Activate script missing; venv had Linux-style layout | First `python` on PATH was MSYS2's Python 3.14 (`E:\msys64\ucrt64\bin`) | Deleted the venv, recreated it with the standard Python 3.11 by full path |
| 7 | `pip install halmos` failed building `safe-pysha3` | No prebuilt Windows wheel; needs Microsoft C++ Build Tools | `pip install halmos --no-deps`, then installed dependencies manually with the `pycryptodome` hash backend |
| 8 | `forge build` printed warnings | Third-party T-REX and library code | No action. Warnings recorded, code left unmodified |

## 8. Phase 0 status

- [x] Foundry and Halmos installed and smoke-tested together
- [x] Node 20 and Python 3.11 environments working
- [x] T-REX 4.1.6 pinned
- [x] Commit hash recorded
- [x] Hardhat baseline: 777 passing
- [x] `forge build` compiles T-REX with Solidity 0.8.17

Next: Phase 1, tracing the `transfer` path through `Token`, `IdentityRegistry`, `ModularCompliance` and the compliance modules.