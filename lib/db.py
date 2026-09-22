"""
Persistence layer. All case data lives in a Supabase (hosted Postgres) table
called 'cases', rather than in a local file — Streamlit Community Cloud does
not guarantee local files survive between deploys, so a hosted database is
what keeps case history intact between now and final submission.

See README.md for the SQL to create the 'cases' table, and for where the
SUPABASE_URL / SUPABASE_KEY values come from.
"""

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_client() -> Client:
    """Create (once) and reuse a single Supabase client for the app's lifetime."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def create_case(case: dict) -> None:
    """Insert a newly submitted case."""
    get_client().table("cases").insert(case).execute()


def get_case(case_id: str):
    """Look up a single case by its case number. Returns None if not found."""
    result = get_client().table("cases").select("*").eq("id", case_id).execute()
    return result.data[0] if result.data else None


def list_cases(stakeholder: str | None = None) -> list[dict]:
    """
    List cases, newest first. Pass a stakeholder name to see only that
    role's queue; pass None (admin) to see every case.
    """
    query = get_client().table("cases").select("*").order("created_at", desc=True)
    if stakeholder:
        query = query.eq("stakeholder", stakeholder)
    return query.execute().data


def update_status(case_id: str, status: str, resolution_note: str | None = None) -> None:
    """Update a case's status, and its resolution note if one is given."""
    updates = {"status": status}
    if resolution_note is not None:
        updates["resolution_note"] = resolution_note
    get_client().table("cases").update(updates).eq("id", case_id).execute()
