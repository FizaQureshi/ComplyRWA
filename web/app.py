import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent

STEPS = [
    "Policy input (K1, K3, J1, H1, H3)",
    "Generated properties (saved tests)",
    "Executed tests (saved results)",
    "Explaining the failures (saved AI answers)",
    "Building the audit report",
]

FIXED_RULES = {
    "K1": "Only investors with a valid KYC claim from a trusted issuer may receive tokens.",
    "K3": "At least one KYC claim topic must be required.",
    "J1": "Investors registered in a restricted country may not receive tokens.",
    "H1": "No investor may hold more than the maximum allowed tokens.",
    "H3": "The holding-limit module's balance records must match the real token balances.",
}
CONFIGS = [f"C{i:02d}" for i in range(1, 9)] + [f"V{i:02d}" for i in range(1, 14)]
NOT_TESTED = {"C03", "C04", "C07", "V11"}

st.set_page_config(
    page_title="ComplyRWA", page_icon=":material/shield:", layout="wide", initial_sidebar_state="expanded"
)

SIDEBAR_WIDTH = 450
CONTENT_WIDTH = 1100
st.markdown(
    f"""
    <style>
    section[data-testid='stSidebar'][aria-expanded='true'] {{
        min-width: {SIDEBAR_WIDTH}px !important;
        max-width: {SIDEBAR_WIDTH}px !important;
        width: {SIDEBAR_WIDTH}px !important;
    }}
    [data-testid='stMainBlockContainer'], .block-container {{
        max-width: {CONTENT_WIDTH}px !important;
        margin-left: auto;
        margin-right: auto;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def config_label(c):
    kind = "clean setup" if c.startswith("C") else "seeded variant"
    return f"{c} ({kind}{', not tested' if c in NOT_TESTED else ''})"


def error_result(stage, message):
    return {"error": {"stage": stage, "message": message}}


def read_json(path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def checklist(active, failed=False):
    lines = []
    for j, s in enumerate(STEPS):
        if j < active:
            lines.append(f":green[✓] {s}")
        elif j == active and failed:
            lines.append(f":red[✗] **{s}** (failed)")
        elif j == active:
            lines.append(f"**→ {s}...**")
        else:
            lines.append(f":gray[○ {s}]")
    return "\n\n".join(lines)


def run_engine(target, engine_python):
    if not (REPO / "pipeline" / "demo.py").exists():
        return error_result("setup", "pipeline/demo.py was not found. Run git pull and try again.")
    cmd = [engine_python, "pipeline/demo.py", "--target", target, "--mode", "replay"]
    box = st.empty()
    last = len(STEPS) - 1
    i = 0
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(
            subprocess.run, cmd, cwd=str(REPO), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300,
        )
        while not fut.done():
            box.markdown(checklist(min(i, last)))
            i += 1
            time.sleep(0.4)
        try:
            proc = fut.result()
        except Exception as e:
            box.markdown(checklist(min(i, last), failed=True))
            return error_result("launch", str(e))

    folder = REPO / "results" / f"demo_{target}"
    try:
        data = read_json(folder / "report.json")
    except ValueError:
        data = None

    if proc.returncode != 0:
        box.markdown(checklist(min(i, last), failed=True))
        if data and data.get("status") == "error":
            return error_result(data.get("step", "demo"), data.get("message", "The audit failed."))
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return error_result("demo", tail[-1] if tail else "The command failed and printed nothing.")
    if not data or data.get("status") != "ok":
        box.markdown(checklist(min(i, last), failed=True))
        return error_result("demo", "report.json is missing or is not marked ok.")

    box.markdown(checklist(len(STEPS)))
    mp = folder / "report.md"
    return {"data": data, "report": mp.read_text(encoding="utf-8") if mp.exists() else ""}


def status_text(s):
    if s == "PASS":
        return ":green[PASS]"
    if s == "FAIL":
        return ":red[**FAIL**]"
    if s in ("NOT_RUN", "NOT RUN"):
        return ":gray[NOT RUN]"
    return s or "-"


KNOWN_KEYS = {"policy", "tests_run", "failed", "status", "severity"}


def rule_note(rid, v, findings):
    parts = []
    de = (findings.get(rid) or {}).get("direct_evidence") or {}
    if v.get("status") == "FAIL" and de.get("direct") == 0:
        parts.append("side effect, not a separate problem")
    for k, val in v.items():
        if k in KNOWN_KEYS or val in (None, "", False, [], {}):
            continue
        label = k.replace("_", " ")
        parts.append(label if val is True else f"{label}: {val}")
    return "; ".join(parts)


def show(result):
    st.divider()
    err = result.get("error")
    if err:
        st.error("The audit failed")
        st.write(f"Stage: {err['stage']}")
        st.code(err["message"])
        st.caption("Check the settings and run the audit again.")
        return

    data, report = result["data"], result["report"]
    rules = data.get("rules", {})
    findings = data.get("findings") if isinstance(data.get("findings"), dict) else {}
    failed = [r for r, v in rules.items() if v.get("status") == "FAIL"]
    passed = [r for r, v in rules.items() if v.get("status") == "PASS"]
    not_run = [r for r, v in rules.items() if v.get("status") in ("NOT_RUN", "NOT RUN")]
    info = data.get("info", [])

    if rules and len(not_run) == len(rules):
        st.warning("Not tested. The saved tests are skipped for this configuration, so this is not a clean result.")
    elif failed:
        st.error(f"{len(failed)} of {len(rules)} rules failed")
    elif info:
        st.success(f"No problems found for these {len(rules)} rules. There are notes for your information.")
    else:
        st.success(f"No findings for these {len(rules)} rules.")
    st.caption(f"Target: {data.get('target', 'unknown')}  |  Model: {data.get('model', '?')}  |  Mode: {data.get('mode', '?')}")
    st.caption("This audit shows saved evidence. It does not run Foundry live.")
    if report:
        st.download_button("Download report.md", report, file_name="report.md", mime="text/markdown")

    tab_status, tab_find, tab_report = st.tabs(["Rule status", "Findings", "Full report"])

    with tab_status:
        cols = st.columns(4)
        cols[0].metric("Rules checked", len(rules))
        cols[1].metric("Passed", len(passed))
        cols[2].metric("Failed", len(failed))
        cols[3].metric("Not tested", len(not_run))

        notes = {rid: rule_note(rid, v, findings) for rid, v in rules.items()}
        has_notes = any(notes.values())
        lines = [
            "| Rule | Policy | Tests run | Tests failed | Status | Severity |" + (" Note |" if has_notes else ""),
            "|---|---|---|---|---|---|" + ("---|" if has_notes else ""),
        ]
        for rid, v in rules.items():
            row = (
                f"| {rid} | {v.get('policy', '')} | {v.get('tests_run', '-')} | {v.get('failed', '-')} "
                f"| {status_text(v.get('status'))} | {v.get('severity') or '-'} |"
            )
            if has_notes:
                row += f" {notes[rid] or '-'} |"
            lines.append(row)
        st.markdown("\n".join(lines))

        groups = data.get("groups", {})
        if groups:
            st.subheader("Grouped findings")
            for name, ids in groups.items():
                st.write(f"**{name}:** {', '.join(ids)}")

        for line in info:
            st.info(line)

        cost = data.get("cost")
        if cost:
            st.caption(
                f"{cost.get('llm_calls', 0)} AI calls, paid \\${cost.get('paid_usd', 0):.4f} this run "
                f"(\\${cost.get('first_made_usd', 0):.4f} when first made), {cost.get('wall_seconds', 0)} s"
            )

    with tab_find:
        if not findings:
            st.write("No findings to show.")
        for n, (rid, f) in enumerate(findings.items()):
            sev = str(f.get("severity") or "UNKNOWN")
            de = f.get("direct_evidence") or {}
            side = de.get("direct") == 0
            title = f"[{sev}] Rule {rid}" + (" (side effect)" if side else "")
            with st.expander(title, expanded=(n == 0)):
                if side:
                    st.info("Side effect, not a separate problem: every failure of this rule comes from another rule's problem.")
                st.markdown((f.get("text") or "").replace("\n", "  \n"))
                if de:
                    st.caption(f"Direct evidence: {de.get('direct', '?')} of {de.get('total', '?')} failing tests")
                tests = f.get("failing_tests") or []
                if tests:
                    st.write("**Failing tests**")
                    for t in tests:
                        tag = " (side effect)" if t.get("side_effect") else ""
                        st.write(f"- `{t.get('name', '')}`{tag}: {t.get('reason', '')}")
                if f.get("reproducible_test"):
                    st.write("**Reproducible test**")
                    st.code(f["reproducible_test"], language="solidity")

    with tab_report:
        if report:
            st.markdown(report)
        else:
            st.write("No report.md was found.")


st.title("ComplyRWA")
st.caption(
    "AI-assisted compliance audit for tokenized real-world assets (ERC-3643 / T-REX). "
    "Check that your contracts really enforce your rules."
)

with st.sidebar:
    st.markdown("**Settings**")
    engine_python = st.text_input("Python for the engine", sys.executable)
    test_error = st.checkbox("Test the error screen (sends an unknown target)")
    st.caption("Replay mode: the audit shows saved evidence. No Foundry and no API key are needed.")

config = st.selectbox("Target configuration", CONFIGS, format_func=config_label)

st.subheader("Policy rules")
st.caption("This version audits these 5 rules. They are fixed because the saved tests were made for exactly these texts.")
rule_lines = ["| Rule | Policy |", "|---|---|"] + [f"| {rid} | {text} |" for rid, text in FIXED_RULES.items()]
st.markdown("\n".join(rule_lines))

if st.button("Run audit", type="primary", icon=":material/play_arrow:"):
    target = "V99" if test_error else config
    with st.status("Running audit (replay of saved evidence)...", expanded=True) as status:
        result = run_engine(target, engine_python)
        if result.get("error"):
            status.update(label="Audit failed", state="error")
        else:
            status.update(label="Audit finished", state="complete")
    st.session_state["result"] = result

if "result" in st.session_state:
    show(st.session_state["result"])
