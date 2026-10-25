"""Dashboard: streamlit run dashboard.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from leadagent import agent, ai, config, db, places

st.set_page_config(page_title="Lead Agent", page_icon="🎯", layout="wide")
conn = db.connect()


def reset(*keys):
    for key in keys:
        st.session_state.pop(key, None)
    st.rerun()


def render_lead(lead: dict):
    lid = lead["id"]
    left, right = st.columns([2, 3])

    with left:
        st.markdown(f"**{lead['category'].title()}** · {lead['address']}")
        st.markdown(f"📞 {lead['phone']}  \n⭐ {lead['rating']} ({lead['reviews']} reviews)")
        if lead["website"]:
            st.markdown(f"🌐 [{lead['website']}]({lead['website']})")
        st.markdown(f"📍 [Open in Google Maps]({lead['maps_url']})")
        st.markdown("**Problems found:**")
        for issue in lead["site_issues"] or ["Website looks fine"]:
            st.markdown(f"- {issue}")

        statuses = db.STATUSES
        new_status = st.selectbox("Status", statuses, index=statuses.index(lead["status"]), key=f"status{lid}")
        notes = st.text_input("Notes", lead["notes"], key=f"notes{lid}")
        if new_status != lead["status"] or notes != lead["notes"]:
            db.update_lead(conn, lid, status=new_status, notes=notes)
            st.rerun()

    with right:
        history = db.get_messages(conn, lid)
        for m in history:
            with st.chat_message("user" if m["direction"] == "in" else "assistant", avatar="🧑‍💼" if m["direction"] == "in" else "🧑‍💻"):
                st.write(m["text"])

        if lead["status"] in ("new", "drafted"):
            draft = st.text_area("First message (edit before sending)", lead["draft"] or "", height=200, key=f"draft{lid}")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("💾 Save", key=f"save{lid}"):
                db.update_lead(conn, lid, draft=draft, status="drafted")
                reset(f"draft{lid}")
            if c2.button("🔄 Rewrite", key=f"rewrite{lid}"):
                with st.spinner("Writing..."):
                    result = agent.draft_pitch(ai.get_brain(), lead)
                db.update_lead(conn, lid, pitch_angle=result["pitch_angle"], draft=result["message"], status="drafted")
                reset(f"draft{lid}")
            if draft:
                c3.link_button("📲 WhatsApp", agent.whatsapp_link(lead, draft))
                if c4.button("✅ I sent it", key=f"sent{lid}", disabled=limit_reached):
                    db.add_message(conn, lid, "out", draft)
                    db.update_lead(conn, lid, draft=draft, status="sent")
                    reset(f"draft{lid}")
            return

        incoming = st.text_area("Paste the client's reply here", key=f"in{lid}")
        if st.button("🤖 Draft my answer", key=f"answer{lid}", disabled=not incoming.strip()):
            db.add_message(conn, lid, "in", incoming.strip())
            if lead["status"] == "sent":
                db.update_lead(conn, lid, status="replied")
            with st.spinner("Writing..."):
                st.session_state[f"replytext{lid}"] = agent.draft_reply(ai.get_brain(), lead, db.get_messages(conn, lid))
            reset(f"in{lid}", f"reply{lid}")

        if f"replytext{lid}" in st.session_state:
            reply = st.text_area(
                "Your answer (check every [CHECK]/[PRICE] gap before sending)",
                st.session_state[f"replytext{lid}"], height=180, key=f"reply{lid}",
            )
            c1, c2 = st.columns(2)
            c1.link_button("📲 WhatsApp", agent.whatsapp_link(lead, reply))
            if c2.button("✅ I sent this reply", key=f"replysent{lid}", disabled="[" in reply):
                db.add_message(conn, lid, "out", reply)
                reset(f"replytext{lid}", f"reply{lid}")
            if "[" in reply:
                c2.caption("Fill in the [ ] gaps first.")


st.title("🎯 Lead Agent")
st.caption("Finds local businesses that need a website and drafts messages. **You** check and send every message.")

counts = db.counts(conn)
sent_today = db.sent_today(conn)
limit_reached = sent_today >= config.DAILY_SEND_LIMIT
cols = st.columns(6)
for col, status in zip(cols, ["new", "drafted", "sent", "replied", "won"]):
    col.metric(status.title(), counts.get(status, 0))
cols[5].metric("Sent today", f"{sent_today}/{config.DAILY_SEND_LIMIT}")
if limit_reached:
    st.warning("Daily send limit reached. Sending too many messages can get your WhatsApp number banned. Continue tomorrow.")

with st.sidebar:
    st.header("Find new leads")
    with st.form("find"):
        category = st.text_input("Business type", "gyms")
        city = st.text_input("City", config.DEFAULT_CITY)
        pages = st.slider("Pages (up to 20 businesses each)", 1, 3, 1)
        draft_n = st.number_input("Draft messages for the top", 0, 50, 10)
        go = st.form_submit_button("🚀 Run agent", use_container_width=True)
    if go:
        if not city.strip():
            st.error("Enter a city.")
        else:
            with st.status("Agent working...", expanded=True) as box:
                try:
                    agent.run(conn, category.strip(), city.strip(), pages, int(draft_n), log=box.write)
                    box.update(label="Done!", state="complete")
                except (places.PlacesError, ai.AIError) as e:
                    box.update(label="Stopped", state="error")
                    st.error(str(e))

    st.header("Show")
    status_filter = st.selectbox("Status", ["drafted", "new", "sent", "replied", "won", "lost", "skipped", "all"])
    min_score = st.slider("Minimum score", 0, 100, 0)

leads = db.list_leads(conn, None if status_filter == "all" else status_filter, min_score)
if not leads:
    st.info("No leads here yet. Use **Run agent** in the sidebar to find some.")
for lead in leads[:100]:
    label = f"{lead['score']} · {lead['name']} · ⭐ {lead['rating']} ({lead['reviews']}) · {lead['site_status'] or 'unchecked'}"
    with st.expander(label):
        render_lead(lead)
