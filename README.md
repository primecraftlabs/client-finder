# Client Finder

An AI agent that finds local businesses that need a website, and drafts outreach messages for you to review and send.

## Setup (once)
```powershell
cd projects\client-finder
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env    # then open .env and fill in your keys and details
```

**Keys you need:**
1. **Gemini (free):** https://aistudio.google.com, then "Get API key", then "Create API key". Paste it as `GEMINI_API_KEY`.
2. **Google Places:** https://console.cloud.google.com, then create a project, enable **Places API (New)**,
   go to Credentials, create an API key, and paste it as `GOOGLE_PLACES_API_KEY`.
   Billing must be enabled, but normal use stays inside the free monthly allowance.
   **Set a budget alert** (Billing, then Budgets & alerts) so you can never be surprised.

## Use
**Dashboard (easiest):**
```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

**Command line:**
```powershell
.\.venv\Scripts\python.exe -m leadagent run "gyms" --city "Jaipur"   # find + check + draft
.\.venv\Scripts\python.exe -m leadagent list                         # best leads
.\.venv\Scripts\python.exe -m leadagent models                       # Gemini models your key can use
```

## Rules built in
- Messages are never sent automatically. You open each one in WhatsApp and press send yourself.
- Daily send limit (`DAILY_SEND_LIMIT`, default 20) protects your number from spam flags.
- Every first message tells the business they can reply "no" and won't be contacted again. Respect that and mark them **lost**.
