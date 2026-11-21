import json
import subprocess
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
REPO = ROOT.parent

STEPS = [
    "Slicing the contract code",
    "Asking the AI to write tests",
    "Filtering out bad tests",
    "Running tests with Foundry",
    "Writing the report",
]

RULES = {
    "K1": "Only investors with a valid KYC claim from a trusted issuer may receive tokens.",
    "K2": "Revoking an investor's KYC must block them from receiving tokens.",
    "K3": "At least one KYC claim topic must be required.",
    "K4": "Expired KYC claims must be rejected.",
    "K5": "An investor whose KYC was revoked must not be able to send tokens.",
    "J1": "Investors registered in a restricted country may not receive tokens.",
    "J2": "A change of an investor's country must be respected by the country rule.",
    "J3": "The country module must be bound and configured.",
    "J4": "A forced transfer by an agent is a known exception and must be labelled as such.",
    "H1": "No investor may hold more than the maximum allowed tokens.",
    "H2": "The cap applies per identity, not per wallet.",
    "H3": "The holding-limit module's balance records must match the real token balances.",
    "H4": "The cap must be set to a sensible number.",
}
DEFAULT_IDS = ["K1", "K3", "J1", "H1", "H3"]
NONE = "(none)"
CONFIGS = [f"C{i:02d}" for i in range(1, 9)] + [f"V{i:02d}" for i in range(1, 14)]
DEMO_TARGETS = ["C01", "V04", "V09"]

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
    return f"{c} (clean setup)" if c.startswith("C") else f"{c} (seeded variant)"


def error_result(stage, message):
    return {"error": {"stage": stage, "message": message}}


def read_folder(folder):
    jp, mp = Path(folder) / "report.json", Path(folder) / "report.md"
    if not jp.exists():
        return None
    data = json.loads(jp.read_text(encoding="utf-8"))
    report = mp.read_text(encoding="utf-8") if mp.exists() else ""
    return {"data": data, "report": report}


def load_demo(target):
    return read_folder(SAMPLES / f"demo_{target}")


def run_real(target, engine_dir, engine_python, log):
    # TO CONFIRM with the engine owner: demo.py currently takes only --target, so the rule rows are not passed yet.
    cmd = [engine_python, "pipeline/demo.py", "--target", target]
    lines = []
    try:
        proc = subprocess.Popen(
            cmd, cwd=engine_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        for line in proc.stdout:
            lines.append(line.rstrip())
            log.code("\n".join(lines[-12:]))
        proc.wait()
    except Exception as e:
        return error_result("launch", str(e))
    result = read_folder(Path(engine_dir) / "results" / f"demo_{target}")
    if result is None:
        return error_result("engine", "\n".join(lines[-10:]) or "The engine did not write report.json.")
    return result


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


def demo_progress(fail=False):
    stop_at = 3 if fail else len(STEPS)
    with st.status("Running audit...", expanded=True) as status:
        bar = st.progress(0)
        box = st.empty()
        for i in range(stop_at):
            box.markdown(checklist(i))
            time.sleep(0.8)
            bar.progress(int((i + 1) / len(STEPS) * 100))
        if fail:
            box.markdown(checklist(stop_at, failed=True))
            status.update(label="Audit failed", state="error")
        else:
            box.markdown(checklist(len(STEPS)))
            status.update(label="Audit finished", state="complete")


def status_text(s):
    if s == "PASS":
        return ":green[PASS]"
    if s == "FAIL":
        return ":red[**FAIL**]"
    return s or "-"


KNOWN_KEYS = {"policy", "tests_run", "failed", "status", "severity"}


def extra_notes(v):
    parts = []
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
    failed = [rid for rid, v in rules.items() if v.get("status") == "FAIL"]
    passed = [rid for rid, v in rules.items() if v.get("status") == "PASS"]
    info = data.get("info", [])

    if failed:
        st.error(f"{len(failed)} of {len(rules)} rules failed")
    elif info:
        st.success("No problems found. There are notes for your information.")
    else:
        st.success("No findings. All rules passed.")
    st.caption(f"Target: {data.get('target', 'unknown')}  |  Model: {data.get('model', '?')}  |  Mode: {data.get('mode', '?')}")
    if report:
        st.download_button("Download report.md", report, file_name="report.md", mime="text/markdown")

    tab_status, tab_report = st.tabs(["Rule status", "Full report"])

    with tab_status:
        cols = st.columns(3)
        cols[0].metric("Rules checked", len(rules))
        cols[1].metric("Passed", len(passed))
        cols[2].metric("Failed", len(failed))

        notes = {rid: extra_notes(v) for rid, v in rules.items()}
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

    with tab_report:
        if report:
            st.markdown(report)
        else:
            st.write("No report.md was found.")


def sync_text(i):
    st.session_state[f"text{i}"] = RULES.get(st.session_state[f"rid{i}"], "")


st.title("ComplyRWA")
st.caption(
    "AI-assisted compliance audit for tokenized real-world assets (ERC-3643 / T-REX). "
    "Check that your contracts really enforce your rules."
)

with st.sidebar:
    mode = st.radio("**Mode**", ["Demo mode (saved results)", "Real audit"])
    is_demo = mode.startswith("Demo")
    if is_demo:
        simulate_fail = st.checkbox("Simulate a failed audit")
        st.caption("Demo mode shows saved results for C01, V04 and V09.")
    else:
        engine_dir = st.text_input("Engine folder", str(REPO))
        engine_python = st.text_input("Python for the engine", "python")

config = st.selectbox("Target configuration", CONFIGS, format_func=config_label)

st.subheader("Policy rules")
st.caption("Pick a rule ID for each row. The text fills in automatically and you can edit it. Use at least 3 rows.")
h1, h2 = st.columns([1, 5])
h1.markdown("**Rule ID**")
h2.markdown("**Policy text**")
for i in range(5):
    st.session_state.setdefault(f"rid{i}", DEFAULT_IDS[i])
    st.session_state.setdefault(f"text{i}", RULES[DEFAULT_IDS[i]])
    c1, c2 = st.columns([1, 5])
    c1.selectbox(
        f"Rule ID {i + 1}", [NONE] + list(RULES), key=f"rid{i}", on_change=sync_text, args=(i,),
        label_visibility="collapsed",
    )
    c2.text_input(f"Rule text {i + 1}", key=f"text{i}", label_visibility="collapsed")
if is_demo:
    st.caption("Demo mode ignores changes to the rules. Saved results use K1, K3, J1, H1 and H3.")

if st.button("Run audit", type="primary", icon=":material/play_arrow:"):
    chosen = []
    for i in range(5):
        rid, text = st.session_state[f"rid{i}"], st.session_state[f"text{i}"].strip()
        if rid != NONE and text:
            chosen.append((rid, text))
    ids = [rid for rid, _ in chosen]
    if len(chosen) < 3:
        st.error("Choose at least 3 rules.")
    elif len(set(ids)) < len(ids):
        st.error("Each rule ID can be used only once.")
    elif is_demo and not simulate_fail and config not in DEMO_TARGETS:
        st.error("Saved demo results exist only for C01, V04 and V09. Pick one of them.")
    elif is_demo:
        demo_progress(fail=simulate_fail)
        if simulate_fail:
            result = error_result("executor", "Foundry could not compile the project.")
        else:
            result = load_demo(config) or error_result("demo", f"web/samples/demo_{config}/report.json is missing.")
        st.session_state["result"] = result
    else:
        with st.status("Running the audit. This can take a few minutes...", expanded=True) as status:
            log = st.empty()
            result = run_real(config, engine_dir, engine_python, log)
            if result.get("error"):
                status.update(label="Audit failed", state="error")
            else:
                status.update(label="Audit finished", state="complete")
        st.session_state["result"] = result

if "result" in st.session_state:
    show(st.session_state["result"])
