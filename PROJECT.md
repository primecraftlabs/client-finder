# Client Finder

- **Type:** Own tool
- **Owner:** Jitender
- **Status:** Code written, not yet run with real API keys
- **Showable:** yes (good showcase: "I built an AI agent that finds business leads")
- **Stack:** Python, Google Places API (New), Gemini API (free tier) or Ollama, SQLite, Streamlit

## What it does
Finds local businesses (e.g. "gyms in Jaipur"), keeps the ones that are busy (enough Google reviews)
and reachable by phone, checks their website for problems, scores them, and drafts a personal
WhatsApp message for each. The dashboard lets the owner edit, open in WhatsApp, and log what was sent.
Client replies can be pasted in and the AI drafts an answer. **Nothing is ever sent automatically.**

## Files
- `leadagent/places.py` - business search
- `leadagent/website_check.py` - finds website problems
- `leadagent/agent.py` - scoring, pipeline, AI prompts, WhatsApp links
- `leadagent/ai.py` - AI brain (Gemini / Ollama, chosen by `AI_PROVIDER`)
- `leadagent/db.py` - SQLite storage (`leads.db`, not committed)
- `dashboard.py` - Streamlit dashboard
- `README.md` - setup and usage
