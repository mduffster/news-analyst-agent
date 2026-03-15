"""CLI entry point for the news analyst pipeline."""

import argparse
import asyncio


def main():
    parser = argparse.ArgumentParser(description="News Analyst Pipeline")
    sub = parser.add_subparsers(dest="command")

    p_onboard = sub.add_parser("onboard", help="Onboard a new topic")
    p_onboard.add_argument("description", help="Topic description")
    p_onboard.add_argument("--slug", help="Override auto-generated slug")

    p_primers = sub.add_parser("primers", help="Generate primer reports")
    p_primers.add_argument("topic", help="Topic slug")

    p_update = sub.add_parser("update", help="Generate daily update")
    p_update.add_argument("topic", nargs="?", help="Topic slug (omit for all)")
    p_update.add_argument("--date", help="Override date (YYYY-MM-DD)")

    sub.add_parser("build", help="Build static site")

    args = parser.parse_args()

    if args.command == "onboard":
        from app.onboard import onboard_topic

        asyncio.run(onboard_topic(args.description, args.slug))
    elif args.command == "primers":
        from app.pipeline import generate_primers

        asyncio.run(generate_primers(args.topic))
    elif args.command == "update":
        if args.topic:
            from app.pipeline import generate_updates

            asyncio.run(generate_updates(args.topic, args.date))
        else:
            from app.pipeline import generate_all_updates

            asyncio.run(generate_all_updates(args.date))
    elif args.command == "build":
        from app.build import build_site

        build_site()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
