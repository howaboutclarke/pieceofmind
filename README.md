# pieceofmind
Anonymous employee feedback, AI-drafted SMART-goal suggestions, and
role-scoped stakeholder dashboards — a standalone Streamlit app.

This README assumes no prior deployment experience. Follow it top to bottom.

## 1. What you'll need accounts for

- **GitHub** — to hold the code (you likely already have this).
- **Groq** — free API access for the AI steps (SMART drafting + prose).
- **Supabase** — free hosted database, so case data survives between
  sessions and redeploys (Streamlit Community Cloud's own storage does not
  guarantee this).

## 2. Get a Groq API key

1. Go to <https://console.groq.com/keys> and sign in (email or Google —
   no credit card needed).
2. Click **Create API Key**, give it any name, and copy the key. You won't
   be able to see it again after this, so paste it somewhere safe for now.

## 3. Set up Supabase

1. Go to <https://supabase.com>, sign up, and create a new project (pick
   any name and a database password — save the password somewhere, though
   you won't need it for this app).
2. Once the project is ready, open the **SQL Editor** (left sidebar) and
   run this to create the table the app expects:

   ```sql
   create table cases (
     id text primary key,
     category text not null,
     stakeholder text not null,
     feedback text not null,
     smart jsonb,
     case_type text not null default 'goal',
     prose text not null,
     status text not null default 'Received',
     notes jsonb not null default '[]',
     resolution_note text,
     created_at timestamptz not null default now()
   );
   ```

   `smart` is nullable and `case_type` distinguishes a normal SMART-goal
   submission (`'goal'`) from a duty-of-care disclosure (`'report'`) that
   bypassed SMART conversion entirely — see the design notes below.

   If you already created the table with the old schema, run this instead
   of dropping it:

   ```sql
   alter table cases alter column smart drop not null;
   alter table cases add column case_type text not null default 'goal';
   ```

3. Go to **Project Settings → API**. You need two values from this page:
   - **Project URL** → this is your `SUPABASE_URL`
   - **anon public key** → this is your `SUPABASE_KEY`

## 4. Run it locally first

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and
   fill in your three real values (`GROQ_API_KEY`, `SUPABASE_URL`,
   `SUPABASE_KEY`). This file is already in `.gitignore`, so it will never
   be committed.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   streamlit run app.py
   ```

   It should open in your browser at `http://localhost:8501`. Try
   submitting a piece of feedback, then open the dashboard with one of the
   demo codes below to see it appear.

## 5. Demo access codes (change these before Demo Day if you want)

Set in `lib/config.py`:

| Role | Code |
|---|---|
| Operations Manager | `OPSQUEUE24` |
| Line Manager | `LINEQUEUE24` |
| HR Manager | `HRQUEUE24` |
| Admin (sees every case) | `PIECEOFMIND` |

## 6. Push the code to GitHub

```bash
git init
git add .
git commit -m "Initial Casefile app"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

Double-check `.streamlit/secrets.toml` (the real one, with your keys) is
**not** included — `git status` should not list it. Only
`secrets.toml.example` should ever be committed.

## 7. Deploy to Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. Click **New app**, pick your repository, branch (`main`), and set the
   main file path to `app.py`.
3. Before (or right after) deploying, open **Advanced settings → Secrets**
   and paste in the same three values as your local `secrets.toml`, in the
   same TOML format:

   ```toml
   GROQ_API_KEY = "..."
   SUPABASE_URL = "..."
   SUPABASE_KEY = "..."
   ```

4. Click **Deploy**. You'll get a public URL — that's what satisfies the
   brief's requirement that the tool be reachable at a URL in a clean
   browser, independent of any AI chat interface.

## 8. Design decisions worth citing in the project outline

- **Anonymity vs. specificity.** A SMART goal is, by nature, specific — and
  in a small team, a specific-enough detail can identify who wrote it. The
  AI never silently generalises anything on the employee's behalf. Instead,
  after drafting (and again after the employee edits the fields), it flags
  when a submission looks specific enough to identify them, states why, and
  requires the employee to either adjust it or explicitly confirm they want
  to continue as-is. Anonymity protection stays under the employee's
  control rather than the system's.
- **Duty-of-care disclosures never become a goal.** Harassment/Discrimination
  and Health & Safety are marked `bypass_smart: True` in `lib/config.py`.
  These skip AI SMART-drafting entirely and go through `generate_report_prose()`
  instead — a plain, factual summary with no proposed solution and no
  softening. This is also why the identifying-risk gate is intentionally
  *not* applied to these categories: pressuring someone disclosing
  harassment or a safety issue to generalise their account could strip out
  exactly the detail a stakeholder needs to act, and could read as pressure
  to stay quiet. Anonymity for these categories relies on the no-names
  writing style and category-based routing, not on withholding detail.

## 9. Known limitations worth being upfront about

- The access-code gate on the dashboard is a UI-level check for this
  prototype, not real authentication — a production version would use
  proper stakeholder sign-in (e.g. company SSO).
- The "email sent" confirmation on submission is simulated — no real email
  is sent. A production version would trigger this through the company's
  actual email system.
