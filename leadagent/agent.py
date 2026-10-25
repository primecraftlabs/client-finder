"""The agent pipeline: find businesses -> check their websites -> score -> draft messages.

The agent never sends anything. You review every message and send it yourself.
"""
import json
import re
from urllib.parse import quote

from . import ai, config, db, places, website_check


def score(lead: dict, site_status: str, issues: list[str]) -> int:
    """0-100. High = busy business (can pay) with a missing or weak website (needs you)."""
    reviews = lead["reviews"]
    s = 30 if reviews >= 200 else 20 if reviews >= 50 else 10
    if lead["rating"] >= 4.0:
        s += 10
    if site_status == "none":
        s += 60
    elif site_status in ("social_only", "unreachable"):
        s += 50
    else:
        s += min(len(issues) * 12, 40)
    return min(s, 100)


def find_leads(conn, category: str, city: str, pages: int = 1, log=print) -> int:
    found = places.search(category, city, pages)
    added = 0
    for lead in found:
        business_status = lead.pop("_business_status")
        if places.is_good_fit(lead, business_status) and db.insert_lead(conn, lead):
            added += 1
    log(f"Found {len(found)} {category} in {city}; {added} new good-fit leads saved.")
    return added


def check_websites(conn, log=print) -> int:
    pending = db.list_leads(conn, where="site_status IS NULL")
    for i, lead in enumerate(pending, 1):
        result = website_check.check(lead["website"])
        db.update_lead(
            conn, lead["id"],
            site_status=result["status"],
            site_issues=result["issues"],
            site_title=result["title"],
            score=score(lead, result["status"], result["issues"]),
        )
        log(f"[{i}/{len(pending)}] {lead['name']}: {result['status']}, {len(result['issues'])} issue(s)")
    return len(pending)


def draft_pitches(conn, limit: int = 10, min_score: int = 40, log=print) -> int:
    leads = db.list_leads(conn, status="new", min_score=min_score, where="site_status IS NOT NULL")[:limit]
    if not leads:
        log("No new leads to draft messages for.")
        return 0
    brain = ai.get_brain()
    for i, lead in enumerate(leads, 1):
        result = draft_pitch(brain, lead)
        db.update_lead(conn, lead["id"], pitch_angle=result["pitch_angle"], draft=result["message"], status="drafted")
        log(f"[{i}/{len(leads)}] Drafted message for {lead['name']} ({result['pitch_angle']})")
    return len(leads)


def run(conn, category: str, city: str, pages: int = 1, draft_limit: int = 10, log=print):
    find_leads(conn, category, city, pages, log)
    check_websites(conn, log)
    draft_pitches(conn, draft_limit, log=log)


def draft_pitch(brain, lead: dict) -> dict:
    portfolio = (
        f"Portfolio: {config.YOUR_PORTFOLIO}" if config.YOUR_PORTFOLIO
        else "No portfolio link yet - do not mention one."
    )
    problems = "\n".join(f"  - {p}" for p in lead["site_issues"]) or "  - none found"
    prompt = f"""You are helping {config.YOUR_NAME}, a freelance web developer, write a first WhatsApp message to a local business owner.

About {config.YOUR_NAME}: offers {config.YOUR_SERVICES}. {portfolio}

The business:
- Name: {lead['name']}
- Type: {lead['category']}, in {lead['city']}
- Google rating: {lead['rating']} from {lead['reviews']} reviews
- Website: {lead['website'] or 'none'}
- Problems found:
{problems}

Write the message in {config.MESSAGE_LANGUAGE}. Rules:
- Under 80 words. Friendly and respectful; it must sound like a real person, not an advert.
- Mention their good reviews and ONE specific problem from the list, and how fixing it can bring them more customers.
- Offer to make a free sample design for their business, with no obligation.
- End with one simple yes/no question, then sign off as "{config.SIGNATURE}".
- Be honest: do not invent facts, past clients, statistics, discounts or deadlines. Do not mention prices.
- Last line: they can simply reply "no" and you won't message again.

Return JSON only: {{"pitch_angle": "<a few words: the problem you focused on>", "message": "<the WhatsApp message>"}}"""
    data = _parse_json(brain.generate(prompt, json_mode=True))
    return {"pitch_angle": data.get("pitch_angle", ""), "message": data.get("message", "").strip()}


def draft_reply(brain, lead: dict, conversation: list[dict]) -> str:
    history = "\n".join(
        f"{config.YOUR_NAME if m['direction'] == 'out' else 'Client'}: {m['text']}" for m in conversation
    )
    prices = config.PRICE_GUIDE or "No prices given. If the client asks about price, write [PRICE] for the developer to fill in."
    prompt = f"""You are helping {config.YOUR_NAME}, a freelance web developer ({config.YOUR_SERVICES}), reply on WhatsApp to the owner of {lead['name']} ({lead['category']} in {lead['city']}).

Conversation so far:
{history}

Price guide: {prices}

Write {config.YOUR_NAME}'s next reply. Rules:
- Short and friendly, in the same language the client used.
- Never promise prices, deadlines or features that are not in the price guide. Where {config.YOUR_NAME} must decide something, write a placeholder like [CHECK: delivery date].
- If the client is not interested, thank them politely and do not push.
- If they are interested, suggest a short call or meeting and ask what time suits them.
- Do not pretend to be anyone other than {config.YOUR_NAME}.

Return only the reply text."""
    return brain.generate(prompt).strip()


def whatsapp_link(lead: dict, text: str) -> str:
    """Opens WhatsApp with the message pre-filled. You still press send yourself."""
    return f"https://wa.me/{lead['intl_phone']}?text={quote(text)}"


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ai.AIError(f"AI did not return valid JSON: {text[:300]}") from e
