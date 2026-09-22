"""
Casefile — anonymous employee feedback, AI-drafted SMART suggestions, and
role-scoped stakeholder dashboards.

Built for the AI in IOP Assignment 2 brief ("Build It"). Run locally with:
    streamlit run app.py
See README.md for setup (Groq + Supabase) and deployment instructions.
"""

import streamlit as st

from lib.config import (
    ROLES,
    CATEGORIES,
    ADMIN_ACCESS_CODE,
    ROLE_ACCESS_CODES,
    STAKEHOLDER_EMAILS,
    STATUS_OPTIONS,
)
from lib.utils import generate_case_number, now_iso
from lib import db, ai

st.set_page_config(page_title="Casefile", page_icon="🗂️", layout="centered")

st.markdown(
    """
    <style>
        .stApp { background-color: #f7f8fa; }
        h1, h2, h3 { color: #12213b; }
        .cf-hint { color: #6b7280; font-size: 0.85rem; margin-top: 0.25rem; }
        .cf-panel {
            background: white; border: 1px solid #e5e7eb; border-radius: 10px;
            padding: 1rem 1.25rem; margin: 0.75rem 0; color: #12213b;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "mode" not in st.session_state:
    st.session_state.mode = "landing"


def go(mode: str) -> None:
    st.session_state.mode = mode
    st.rerun()


# ------------------------------------------------------------------ LANDING
def render_landing() -> None:
    st.title("Casefile")
    st.write(
        "A private way to raise workplace feedback — and a place for the "
        "right stakeholder to act on it."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Submit anonymous feedback", use_container_width=True):
            go("submit")
    with col2:
        if st.button("Stakeholder dashboard", use_container_width=True):
            go("dashboard_login")

    st.divider()
    with st.expander("Check on a case you've already submitted"):
        lookup_id = st.text_input("Case number", key="lookup_id")
        if st.button("Look up case"):
            case = db.get_case(lookup_id.strip().upper())
            if case:
                st.success(f"Status: {case['status']}")
                if case.get("resolution_note"):
                    st.write(case["resolution_note"])
            else:
                st.error(
                    "No case found with that number. Double-check it and try again."
                )


# ------------------------------------------------------------------ SUBMIT WIZARD
def render_submit() -> None:
    st.title("Submit feedback")
    step = st.session_state.get("wizard_step", "feedback")

    if step == "feedback":
        st.write(
            "Step 1 of 4 — Tell us what's going on. No names, please — "
            "yours or anyone else's."
        )
        category_labels = [c["label"] for c in CATEGORIES]
        chosen_label = st.selectbox("What's this about?", category_labels)
        category = next(c for c in CATEGORIES if c["label"] == chosen_label)
        feedback_text = st.text_area("Your feedback", height=180, key="feedback_text")

        stakeholder = category["stakeholder"]
        if stakeholder is None:
            stakeholder = st.selectbox("Who should this go to?", ROLES)

        if st.button("Continue", type="primary"):
            if not feedback_text.strip():
                st.error("Please enter your feedback before continuing.")
            else:
                st.session_state.case_category = category["label"]
                st.session_state.case_stakeholder = stakeholder
                st.session_state.case_feedback = feedback_text.strip()

                if category["bypass_smart"]:
                    # Duty-of-care disclosure — never reframed as a SMART goal.
                    st.session_state.case_is_report = True
                    with st.spinner("Preparing this for the stakeholder..."):
                        st.session_state.case_prose = ai.generate_report_prose(
                            st.session_state.case_feedback, st.session_state.case_category
                        )
                    st.session_state.wizard_step = "review"
                else:
                    st.session_state.case_is_report = False
                    with st.spinner("Drafting a SMART-format suggestion from your feedback..."):
                        st.session_state.case_smart = ai.draft_smart(
                            st.session_state.case_feedback
                        )
                    with st.spinner("Checking for identifying detail..."):
                        st.session_state.case_risk = ai.assess_identifying_risk(
                            st.session_state.case_feedback, st.session_state.case_smart
                        )
                    st.session_state.wizard_step = "smart"
                st.rerun()

        if st.button("Cancel and go back"):
            go("landing")

    elif step == "smart":
        st.write("Step 2 of 4 — Review and refine the suggested solution.")

        gate = st.session_state.get("case_risk_gate_active", False)
        initial_risk = st.session_state.get("case_risk", {})
        if initial_risk.get("identifying_risk") and not gate:
            reason = initial_risk.get("reason")
            st.warning(
                "This draft may be specific enough to identify you in a small team"
                + (f" — {reason}" if reason else "")
                + ". Review the fields below before continuing."
            )

        smart = st.session_state.case_smart
        labels = {
            "specific": "Specific",
            "measurable": "Measurable",
            "achievable": "Achievable",
            "relevant": "Relevant",
            "timebound": "Time-bound",
        }
        for key, label in labels.items():
            field = smart.get(key, {"text": "", "source": "needs_input"})
            hint = (
                " (drafted from your feedback)"
                if field.get("source") == "from_feedback"
                else " (please fill this in)"
            )
            st.text_area(
                f"{label}{hint}", value=field.get("text", ""), key=f"smart_{key}"
            )

        ack = True
        if gate:
            recheck = st.session_state.get("case_risk_recheck", {})
            reason = recheck.get("reason")
            st.warning(
                "This still looks specific enough to identify you"
                + (f" — {reason}" if reason else "")
                + ". Adjust the fields above, or confirm below to continue as-is."
            )
            ack = st.checkbox(
                "I've reviewed this and I'm comfortable continuing.", key="risk_ack"
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back"):
                st.session_state.wizard_step = "feedback"
                st.session_state.pop("case_risk_gate_active", None)
                st.rerun()
        with col2:
            button_label = "Continue anyway" if gate else "Continue"
            if st.button(button_label, type="primary", disabled=(gate and not ack)):
                edited_smart_final = {
                    k: {"text": st.session_state[f"smart_{k}"]} for k in labels
                }
                proceed = True
                if not gate:
                    with st.spinner("Checking your edits..."):
                        recheck = ai.assess_identifying_risk(
                            st.session_state.case_feedback, edited_smart_final
                        )
                    if recheck.get("identifying_risk"):
                        st.session_state.case_risk_gate_active = True
                        st.session_state.case_risk_recheck = recheck
                        proceed = False
                        st.rerun()
                if proceed:
                    st.session_state.case_smart_final = edited_smart_final
                    st.session_state.pop("case_risk_gate_active", None)
                    with st.spinner("Writing up your submission..."):
                        st.session_state.case_prose = ai.generate_prose(
                            st.session_state.case_feedback,
                            st.session_state.case_smart_final,
                            st.session_state.case_category,
                        )
                    st.session_state.wizard_step = "review"
                    st.rerun()

    elif step == "review":
        is_report = st.session_state.get("case_is_report", False)
        step_label = "Step 2 of 3" if is_report else "Step 3 of 4"
        st.write(f"{step_label} — Here's how this will read to the stakeholder.")
        st.markdown(
            f'<div class="cf-panel">{st.session_state.case_prose}</div>',
            unsafe_allow_html=True,
        )
        if not is_report and st.session_state.get("case_smart_final"):
            with st.expander("SMART breakdown"):
                for key, val in st.session_state.case_smart_final.items():
                    st.write(f"**{key.title()}:** {val['text']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back"):
                st.session_state.wizard_step = "feedback" if is_report else "smart"
                st.rerun()
        with col2:
            if st.button("Submit", type="primary"):
                case_id = generate_case_number()
                db.create_case(
                    {
                        "id": case_id,
                        "category": st.session_state.case_category,
                        "stakeholder": st.session_state.case_stakeholder,
                        "feedback": st.session_state.case_feedback,
                        "smart": st.session_state.get("case_smart_final"),
                        "case_type": "report" if is_report else "goal",
                        "prose": st.session_state.case_prose,
                        "status": "Received",
                        "notes": [],
                        "resolution_note": None,
                        "created_at": now_iso(),
                    }
                )
                st.session_state.confirm_case_id = case_id
                st.session_state.confirm_stakeholder = st.session_state.case_stakeholder
                for key in [
                    "case_category",
                    "case_stakeholder",
                    "case_feedback",
                    "case_smart",
                    "case_smart_final",
                    "case_prose",
                    "case_is_report",
                    "case_risk",
                    "case_risk_gate_active",
                    "case_risk_recheck",
                    "risk_ack",
                ]:
                    st.session_state.pop(key, None)
                st.session_state.wizard_step = "confirm"
                st.rerun()

    elif step == "confirm":
        st.success("Your feedback has been submitted.")
        st.write(
            f"Case number: **{st.session_state.confirm_case_id}** — save this "
            "to check on it later. It can't be linked back to you."
        )
        email = STAKEHOLDER_EMAILS.get(
            st.session_state.confirm_stakeholder, "the assigned stakeholder"
        )
        st.markdown(
            f'<div class="cf-panel">✅ Your email has been successfully sent to '
            f'<b>{email}</b>'
            f'<div class="cf-hint">Simulated for this prototype — a production '
            f"deployment would send this through the company's real email system."
            f"</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("Back to home"):
            st.session_state.pop("wizard_step", None)
            go("landing")


# ------------------------------------------------------------------ DASHBOARD LOGIN
def render_dashboard_login() -> None:
    st.title("Stakeholder sign-in")
    role_choice = st.selectbox("Your role", ["All cases (admin)"] + ROLES)
    code = st.text_input("Access code", type="password")

    if st.button("Sign in", type="primary"):
        entered = code.strip().upper()
        is_admin = entered == ADMIN_ACCESS_CODE
        role_key = "all" if role_choice == "All cases (admin)" else role_choice
        is_valid_role_code = (
            role_key != "all" and entered == ROLE_ACCESS_CODES.get(role_key)
        )
        if is_admin or is_valid_role_code:
            st.session_state.dashboard_role = "all" if is_admin else role_key
            go("dashboard")
        else:
            st.error(
                "Only the admin code can open the all-cases view."
                if role_key == "all"
                else "That access code is not recognised for this role."
            )

    st.markdown(
        '<p class="cf-hint">Prototype note: this is a UI-level gate for demo '
        "purposes, not production authentication — a real deployment would "
        "verify stakeholders through company SSO.</p>",
        unsafe_allow_html=True,
    )
    if st.button("Back"):
        go("landing")


# ------------------------------------------------------------------ DASHBOARD
def render_dashboard() -> None:
    role = st.session_state.get("dashboard_role", "all")
    st.title("Stakeholder dashboard")
    st.caption(f"Viewing as: {role if role != 'all' else 'All cases (admin)'}")

    cases = db.list_cases(None if role == "all" else role)

    status_filter = st.selectbox("Filter by status", ["All"] + STATUS_OPTIONS)
    if status_filter != "All":
        cases = [c for c in cases if c["status"] == status_filter]

    if not cases:
        st.info("No cases to show.")

    for case in cases:
        with st.expander(f"{case['id']} — {case['category']} — {case['status']}"):
            st.write(case["prose"])
            new_status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(case["status"]),
                key=f"status_{case['id']}",
            )
            resolution_note = case.get("resolution_note") or ""
            if new_status == "Resolved":
                resolution_note = st.text_area(
                    "Resolution note (shown to the employee)",
                    value=resolution_note,
                    key=f"note_{case['id']}",
                )
            if st.button("Save", key=f"save_{case['id']}"):
                if new_status == "Resolved" and not resolution_note.strip():
                    st.error(
                        "A resolution note is required to mark a case Resolved."
                    )
                else:
                    db.update_status(
                        case["id"], new_status, resolution_note.strip() or None
                    )
                    st.rerun()

    if st.button("Sign out"):
        st.session_state.pop("dashboard_role", None)
        go("landing")


# ------------------------------------------------------------------ ROUTER
mode = st.session_state.mode
if mode == "landing":
    render_landing()
elif mode == "submit":
    render_submit()
elif mode == "dashboard_login":
    render_dashboard_login()
elif mode == "dashboard":
    if "dashboard_role" not in st.session_state:
        go("dashboard_login")
    else:
        render_dashboard()
