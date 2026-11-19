#!/usr/bin/env python3
"""List saved postings whose title matches a pattern, newest first.

Usage:  python3 find_postings.py "partnership|licensing" [--since 2026-11-01] [--place "san francisco|remote"]
Reads:  postings.jsonl, written by pull_boards.py.
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PAY = re.compile(r"\$\s?\d{2,3}(?:,\d{3})?(?:\.\d+)?\s?[kK]?\s*(?:-|–|—|to|and)\s*\$?\s?\d{2,3}(?:,\d{3})?(?:\.\d+)?\s?[kK]?")


def main():
    ap = argparse.ArgumentParser(description="List saved postings whose title matches a pattern, newest first.")
    ap.add_argument("title", help="a regular expression matched against the job title, ignoring case")
    ap.add_argument("--since", default="", help="only postings published on or after this date (YYYY-MM-DD)")
    ap.add_argument("--place", default="", help="a regular expression matched against location and workplace")
    args = ap.parse_args()
    title = re.compile(args.title, re.I)
    place = re.compile(args.place, re.I) if args.place else None

    rows = []
    for line in open(os.path.join(HERE, "postings.jsonl"), encoding="utf-8"):
        p = json.loads(line)
        if not title.search(p["title"]):
            continue
        if args.since and p["published"] < args.since:
            continue
        where = (p["location"] + " " + p["workplace"]).strip()
        if place and not place.search(where):
            continue
        stated = PAY.search(p["text"])
        pay = p["pay"] or (stated.group(0) if stated else "")
        rows.append((p["published"], p["board"], p["title"][:70], where[:44], pay[:32].replace("\n", " "), p["id"][:8]))

    rows.sort(reverse=True)
    print(len(rows), "postings")
    for published, board, name, where, pay, short_id in rows:
        print(" | ".join((published, board, name, where, pay, "%s:%s" % (board, short_id))))


if __name__ == "__main__":
    main()
