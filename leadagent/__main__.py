"""Command line: python -m leadagent <command>"""
import argparse
import sys

from . import agent, ai, config, db, places


def main():
    parser = argparse.ArgumentParser(prog="leadagent", description="Find local businesses that need a website.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="find + check websites + draft messages")
    run.add_argument("category", help='business type, e.g. "gyms"')
    run.add_argument("--city", default=config.DEFAULT_CITY)
    run.add_argument("--pages", type=int, default=1, help="20 businesses per page, max 3")
    run.add_argument("--draft", type=int, default=10, help="how many messages to draft")

    find = sub.add_parser("find", help="only search for businesses")
    find.add_argument("category")
    find.add_argument("--city", default=config.DEFAULT_CITY)
    find.add_argument("--pages", type=int, default=1)

    sub.add_parser("check", help="check websites of leads not checked yet")

    draft = sub.add_parser("draft", help="draft messages for the best new leads")
    draft.add_argument("--limit", type=int, default=10)

    show = sub.add_parser("list", help="show the best leads")
    show.add_argument("--limit", type=int, default=20)

    sub.add_parser("models", help="list the Gemini models your API key can use")

    args = parser.parse_args()
    if getattr(args, "city", "x") == "":
        parser.error("give --city or set DEFAULT_CITY in .env")

    conn = db.connect()
    try:
        if args.cmd == "run":
            agent.run(conn, args.category, args.city, args.pages, args.draft)
        elif args.cmd == "find":
            agent.find_leads(conn, args.category, args.city, args.pages)
        elif args.cmd == "check":
            agent.check_websites(conn)
        elif args.cmd == "draft":
            agent.draft_pitches(conn, args.limit)
        elif args.cmd == "list":
            for lead in db.list_leads(conn)[: args.limit]:
                print(f"{lead['score']:>3}  {lead['status']:<8} {lead['name']} ({lead['reviews']} reviews) "
                      f"- {lead['site_status'] or 'unchecked'}")
        elif args.cmd == "models":
            print("\n".join(ai.GeminiBrain.list_models()))
    except (places.PlacesError, ai.AIError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
