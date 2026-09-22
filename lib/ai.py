"""
AI-assisted steps, called via the Groq API (not a local model — see README
for why that matters once this is deployed to Streamlit Community Cloud).

Two jobs:
1. draft_smart()     — turn raw employee feedback into a draft SMART-format
                        suggested solution, before the employee sees it.
2. generate_prose()  — once the employee has reviewed/edited the SMART
                        fields, turn everything into flowing prose for the
                        stakeholder, with the SMART breakdown woven in.
"""

import json
import streamlit as st
from groq import Groq

# Llama 3.3 70B on Groq: a good balance of quality and speed for this use
# case, and comfortably within Groq's free tier for a class project.
MODEL = "llama-3.3-70b-versatile"


@st.cache_resource
def get_client() -> Groq:
    return Groq(api_key=st.secrets["GROQ_API_KEY"])


SMART_SYSTEM_PROMPT = """You help an employee turn a piece of workplace feedback into a \
SMART-goal-format suggested solution (Specific, Measurable, Achievable, Relevant, Time-bound).

For each SMART element, only fill in a draft from the feedback if it is genuinely \
inferable from what the employee wrote. If it isn't, say so honestly rather than \
inventing detail — mark it as needing the employee's input.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{
  "specific":   {"text": "...", "source": "from_feedback" or "needs_input"},
  "measurable": {"text": "...", "source": "from_feedback" or "needs_input"},
  "achievable": {"text": "...", "source": "from_feedback" or "needs_input"},
  "relevant":   {"text": "...", "source": "from_feedback" or "needs_input"},
  "timebound":  {"text": "...", "source": "from_feedback" or "needs_input"}
}"""


def draft_smart(feedback_text: str) -> dict:
    """Ask Groq to draft SMART fields from raw feedback. Returns a dict."""
    client = get_client()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SMART_SYSTEM_PROMPT},
            {"role": "user", "content": feedback_text},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(completion.choices[0].message.content)


RISK_SYSTEM_PROMPT = """You check whether a piece of anonymous employee feedback, together with its \
SMART-goal breakdown, is specific enough that a colleague or manager could realistically guess who \
wrote it — for example, naming a rare role, an exact meeting, a one-off incident, or a very small \
team. This matters most in small organisations, where a handful of specific details can point \
straight at one person.

You are not deciding whether to change anything yourself — only flagging the risk so the employee \
can review it themselves.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{"identifying_risk": true or false, "reason": "one short, specific sentence, or empty string if none"}"""


def assess_identifying_risk(feedback_text: str, smart: dict) -> dict:
    """
    Flag whether a SMART draft is specific enough to identify the employee.
    This never rewrites anything itself — it only flags, so the employee stays
    in control of the anonymity/specificity trade-off (see README).
    """
    client = get_client()
    user_content = (
        f"Feedback:\n{feedback_text}\n\nSMART breakdown:\n{json.dumps(smart, indent=2)}"
    )
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": RISK_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return json.loads(completion.choices[0].message.content)


REPORT_SYSTEM_PROMPT = """You write a concise, factual, professional summary (South African English \
spelling) of an anonymous employee disclosure, for a stakeholder who may need to act on it urgently.

This is NOT a SMART goal. Do not propose solutions, do not soften or reframe what was said, and do \
not editorialise. Preserve the substance of what the employee described as faithfully as possible, \
in 1 to 3 short paragraphs.

Never name or guess at any individual's identity. But do not strip out specific, safety-relevant \
detail (what happened, when, how often) purely to protect anonymity — the stakeholder needs enough \
detail to act on a disclosure like this."""


def generate_report_prose(feedback_text: str, category_label: str) -> str:
    """
    Turn a duty-of-care disclosure (harassment, safety, etc.) into a plain factual
    report — used instead of generate_prose() for categories where bypass_smart is
    True, so these are never reframed as a goal.
    """
    client = get_client()
    user_content = f"Category: {category_label}\n\nEmployee disclosure:\n{feedback_text}"
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )
    return completion.choices[0].message.content.strip()


PROSE_SYSTEM_PROMPT = """You write concise, professional, flowing prose (South African English \
spelling — e.g. 'favour', 'organise', 'colour') that presents a piece of anonymous employee \
feedback to the stakeholder who will act on it.

Write 2 to 4 short paragraphs. Never name or guess at any individual's identity, including the \
employee, their manager, or colleagues. Weave the SMART-goal breakdown into the prose naturally \
rather than listing it out."""


def generate_prose(feedback_text: str, smart: dict, category_label: str) -> str:
    """Ask Groq to turn the feedback + SMART fields into stakeholder-ready prose."""
    client = get_client()
    user_content = (
        f"Category: {category_label}\n\n"
        f"Employee feedback:\n{feedback_text}\n\n"
        f"SMART breakdown:\n{json.dumps(smart, indent=2)}"
    )
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": PROSE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
    )
    return completion.choices[0].message.content.strip()
