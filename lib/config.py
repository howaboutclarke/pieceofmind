"""
Static configuration for Casefile.

Keeping all of this in one place makes it easy to change categories, routing,
or demo codes without touching the app logic in app.py.
"""

# The three stakeholder roles who can log into the dashboard.
ROLES = ["Operations Manager", "Line Manager", "HR Manager"]

# Feedback categories and which stakeholder each one routes to.
# "stakeholder": None means the employee picks who it goes to (see app.py).
#
# "bypass_smart": True marks a duty-of-care category (harassment, bullying,
# a safety concern) that must never be reframed as a SMART goal. These skip
# the AI SMART-drafting step entirely and go to the stakeholder as a plain,
# factual report instead.
CATEGORIES = [
    {"key": "workload", "label": "Workload & Capacity", "stakeholder": "Line Manager", "bypass_smart": False},
    {"key": "management", "label": "Management & Leadership", "stakeholder": "HR Manager", "bypass_smart": False},
    {"key": "policy", "label": "Company Policy", "stakeholder": "HR Manager", "bypass_smart": False},
    {"key": "safety", "label": "Health & Safety", "stakeholder": "Operations Manager", "bypass_smart": True},
    {"key": "harassment", "label": "Harassment or Discrimination", "stakeholder": "HR Manager", "bypass_smart": True},
    {"key": "other", "label": "Something Else", "stakeholder": None, "bypass_smart": False},
]

# Demo-only access codes. The admin code can view every stakeholder's queue;
# each role code can only view its own. See README for why this is a
# prototype-level gate, not real authentication.
ADMIN_ACCESS_CODE = "PIECEOFMIND"

ROLE_ACCESS_CODES = {
    "Operations Manager": "OPSQUEUE24",
    "Line Manager": "LINEQUEUE24",
    "HR Manager": "HRQUEUE24",
}

# Used only for the simulated "email sent" confirmation message.
STAKEHOLDER_EMAILS = {
    "Operations Manager": "operations@company.com",
    "Line Manager": "linemanager@company.com",
    "HR Manager": "hr@company.com",
}

STATUS_OPTIONS = ["Received", "In Review", "Resolved"]
