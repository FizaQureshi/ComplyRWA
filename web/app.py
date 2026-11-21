import json
import subprocess
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
OUT = ROOT / "out"
REPO = ROOT.parent

STEPS = [
    "Slicing the contract code",
    "Asking the AI to write tests",
    "Filtering out bad tests",
    "Running tests with Foundry",
    "Writing the report",
]

RULES = {
    "K1": "Only fully verified investors may receive tokens.",
    "K2": "Revoking an investor's KYC must block them from receiving tokens.",
    "K3": "At least one KYC claim topic must be required.",
    "K4": "Expired KYC claims must be rejected.",
    "K5": "An investor whose KYC was revoked must not be able to send tokens.",
    "J1": "Investors registered in a restricted country may not receive tokens.",
    "J2": "A change of an investor's country must be respected by the country rule.",
    "J3": "The country module must be bound and configured.",
    "J4": "A forced transfer by an agent is a known exception and must be labelled as such.",
    "H1": "No investor may hold more than the cap.",
    "H2": "The cap applies per identity, not per wallet.",
    "H3": "The holding-limit module's balance records must match the real token balances.",
    "H4": "The cap must be set to a sensible number.",
}
DEFAULT_IDS = ["K1", "K3", "J1", "H1", "H3"]
NONE = "(none)"
CONFIGS = [f"C{i:02d}" for i in range(1, 9)] + [f"V{i:02d}" for i in range(1, 14)]

st.set_page_config(page_title="ComplyRWA", layout="wide")


def config_label(c):
    return f"{c} (clean setup)" if c.startswith("C") else f"{c} (seeded variant)"


def find(pattern):
    hits = sorted(SAMPLES.glob(pattern))
    return hits[0] if hits else None


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def failed_result(message, stage):
    return {
        "audit": {"status": "failed", "error": {"stage": stage, "message": message}},
        "summary": {"verdict": "ERROR"},
        "policy": {"rules": []},
        "properties": [],
        "findings": [],
    }


def make_report(res):
    s = res.get("summary", {})
    lines = ["# ComplyRWA Audit Report", "", f"**Verdict: {s.get('verdict')}**", ""]
    err = res.get("audit", {}).get("error")
    if err:
        lines += [f"The audit failed at stage `{err['stage']}`: {err['message']}", ""]
    for f in res.get("findings", []):
        lines += [
            f"## {f['id']} ({f['severity'].upper()}): {f['title']}",
            "",
            f["explanation"],
            "",
            f"Suggested fix: {f.get('suggested_fix', '')}",
            "",
        ]
    return "\n".join(lines)


def demo_result(kind):
    if kind == "Audit failed":
        res = failed_result("Foundry could not compile the project. Check the project folder.", "executor")
        return res, make_report(res), None
    pattern = "results?sample.json" if kind == "Problems found" else "results?clean?sample.json"
    res = read_json(find(pattern))
    if res is None:
        return None, "", None
    cost = read_json(find("cost?sample.json"))
    if kind == "Problems found":
        rp = find("report?sample.md")
        report = rp.read_text(encoding="utf-8") if rp else make_report(res)
        return res, report, cost
    if kind == "No findings":
        res["findings"] = []
        res["summary"].update(
            verdict="PASS", findings_total=0, findings_by_severity={"high": 0, "medium": 0, "info": 0}
        )
    return res, make_report(res), cost


def build_policy(texts):
    return {"rules": texts}


def build_command(engine_python, project, policy, config):
    # TO CONFIRM with the engine owner: the exact flag name for the target configuration.
    return [engine_python, "complyrwa.py", "audit", "--project", project, "--policy", str(policy),
            "--out", str(OUT), "--config", config]


def run_real(project, texts, config, engine_dir, engine_python):
    OUT.mkdir(exist_ok=True)
    policy = OUT / "policy.json"
    policy.write_text(json.dumps(build_policy(texts), indent=2), encoding="utf-8")
    for old in ("results.json", "report.md", "cost.json"):
        (OUT / old).unlink(missing_ok=True)
    cmd = build_command(engine_python, project, policy, config)
    try:
        proc = subprocess.run(cmd, cwd=engine_dir, capture_output=True, text=True, timeout=1800)
    except Exception as e:
        return failed_result(str(e), "launch"), "", None
    if not (OUT / "results.json").exists():
        msg = (proc.stderr or proc.stdout or "The engine did not write results.json.")[-500:]
        return failed_result(msg, "engine"), "", None
    res = read_json(OUT / "results.json")
    rp, cp = OUT / "report.md", OUT / "cost.json"
    report = rp.read_text(encoding="utf-8") if rp.exists() else make_report(res)
    return res, report, (read_json(cp) if cp.exists() else None)


def show(res, report, cost):
    if res is None:
        st.error("Sample files not found. Put them in web/samples/ and run again.")
        return
    st.divider()
    s = res.get("summary", {})
    verdict = s.get("verdict")
    if verdict == "FAIL":
        st.error(f"{s.get('findings_total', 0)} problem(s) found")
    elif verdict == "PASS_WITH_NOTES":
        st.success("No problems found. There are notes for your information.")
    elif verdict == "PASS":
        st.success("No findings. All tests passed.")
    else:
        err = res.get("audit", {}).get("error") or {}
        st.error("The audit failed")
        st.write(f"Stage: {err.get('stage', 'unknown')}")
        st.code(err.get("message", "No details"))
        st.caption("Check the project folder and run the audit again.")
        return

    audit = res.get("audit", {})
    target = audit.get("target", {})
    st.caption(f"Target: {target.get('config_label', 'unknown')}  |  Duration: {audit.get('duration_seconds', '?')} s")
    st.download_button("Download report.md", report, file_name="report.md", mime="text/markdown", key="dl_top")

    tab_sum, tab_find, tab_tests, tab_rep = st.tabs(["Summary", "Findings", "Generated tests", "Full report"])

    with tab_sum:
        cols = st.columns(4)
        cols[0].metric("Rules checked", s.get("rules_checked", 0))
        cols[1].metric("Tests generated", s.get("properties_generated", 0))
        cols[2].metric("Tests valid", s.get("properties_valid", 0))
        cols[3].metric("Findings", s.get("findings_total", 0))
        totals = (cost or {}).get("totals")
        if totals:
            st.caption(
                f"{totals['input_tokens'] + totals['output_tokens']:,} tokens, "
                f"${totals['usd']:.2f}, {totals['seconds']} seconds"
            )

    with tab_find:
        findings = res.get("findings", [])
        if not findings:
            st.write("No findings to show.")
        for i, f in enumerate(findings):
            with st.expander(f"[{f['severity'].upper()}] {f['title']}", expanded=(i == 0)):
                if f.get("classification") == "known_exception":
                    st.caption("Known exception: shown for your information, not a bug.")
                st.write(f"**Rule violated:** {f.get('policy_violated', '')}")
                st.write(f.get("explanation", ""))
                st.write("**Affected functions:** " + ", ".join(f"`{x}`" for x in f.get("affected_functions", [])))
                st.write("**Steps to reproduce**")
                for stp in f.get("sequence", []):
                    st.write(f"{stp['step']}. `{stp['call']}` ({stp['caller']}): {stp['result']}")
                if f.get("reproduce"):
                    st.code(f["reproduce"]["command"], language="bash")
                st.info(f"**Suggested fix:** {f.get('suggested_fix', '')}")

    with tab_tests:
        props = res.get("properties", [])
        if props:
            st.dataframe(
                [
                    {
                        "ID": p["id"],
                        "Rule": p["rule_id"],
                        "Type": p["kind"],
                        "Test": p["name"],
                        "Status": p["status"],
                        "Note": p.get("rejected_reason") or "",
                    }
                    for p in props
                ],
                hide_index=True,
            )
        else:
            st.write("No generated tests to show.")

    with tab_rep:
        st.markdown(report)


def sync_text(i):
    st.session_state[f"text{i}"] = RULES.get(st.session_state[f"rid{i}"], "")


st.title("ComplyRWA audit")
st.caption("Check whether your ERC-3643 contracts really enforce your rules.")

with st.sidebar:
    mode = st.radio("Mode", ["Demo mode (sample files)", "Real audit"])
    is_demo = mode.startswith("Demo")
    if is_demo:
        demo_kind = st.selectbox("Demo result", ["Problems found", "Clean with notes", "No findings", "Audit failed"])
    else:
        engine_dir = st.text_input("Engine folder", str(REPO))
        engine_python = st.text_input("Python for the engine", "python")

project = st.text_input("Project folder", "./T-REX")
config = st.selectbox("Target configuration", CONFIGS, format_func=config_label)

st.subheader("Policy rules")
st.caption("Pick a rule ID for each row. The text fills in automatically and you can edit it. Use at least 3 rows.")
for i in range(5):
    st.session_state.setdefault(f"rid{i}", DEFAULT_IDS[i])
    st.session_state.setdefault(f"text{i}", RULES[DEFAULT_IDS[i]])
    c1, c2 = st.columns([1, 5])
    c1.selectbox(f"Rule ID {i + 1}", [NONE] + list(RULES), key=f"rid{i}", on_change=sync_text, args=(i,))
    c2.text_input(f"Rule text {i + 1}", key=f"text{i}")

if st.button("Run audit", type="primary"):
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
    elif not project.strip():
        st.error("Enter a project folder.")
    elif is_demo:
        with st.status("Running audit...", expanded=True) as status:
            for step in STEPS:
                st.write(step)
                time.sleep(0.6)
            status.update(label="Audit finished", state="complete")
        st.session_state["result"] = demo_result(demo_kind)
    else:
        with st.spinner("Running the audit. This can take a few minutes..."):
            st.session_state["result"] = run_real(
                project.strip(), [t for _, t in chosen], config, engine_dir, engine_python
            )

if "result" in st.session_state:
    show(*st.session_state["result"])
