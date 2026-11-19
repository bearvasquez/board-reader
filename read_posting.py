#!/usr/bin/env python3
"""Print a digest of chosen postings: a summary, the lines that state requirements, place and pay.

Usage:  python3 read_posting.py [--full] board:id-prefix [board:id-prefix ...]
        python3 read_posting.py --status board:id-prefix ...     (says whether each is still on its board)
Reads:  postings.jsonl, written by pull_boards.py. find_postings.py prints each posting's board:id-prefix.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REQUIRES = re.compile(r"\d\s*\+?\s*(?:-|–|to)?\s*\d*\s*\+?\s*years|\bdegree\b|must have|\brequired\b|\bminimum\b|"
                      r"\bfluen(?:t|cy)\b|clearance|citizen|authorized to work|work authorization|\bvisa\b|sponsor|"
                      r"willing(?:ness)? to (?:travel|relocate)|travel up to|deadline|apply by", re.I)
PLACE = re.compile(r"hybrid|on-?site|in[- ]office|in person|days (a|per) week|remote", re.I)
PAY = re.compile(r"\$\s?\d{2,3}(?:,\d{3})?(?:\.\d+)?\s?[kK]?\s*(?:-|–|—|to)\s*\$?\s?\d{2,3}(?:,\d{3})?\s?[kK]?")


def main():
    args = sys.argv[1:]
    full, status = "--full" in args, "--status" in args
    wanted = [a for a in args if not a.startswith("--")]
    if not wanted:
        raise SystemExit(__doc__)

    by_board = {}
    for line in open(os.path.join(HERE, "postings.jsonl"), encoding="utf-8"):
        p = json.loads(line)
        by_board.setdefault(p["board"], []).append(p)

    for want in wanted:
        board, _, prefix = want.partition(":")
        hits = [p for p in by_board.get(board, []) if p["id"].startswith(prefix)]
        if status:
            print(want, "->", ("OPEN: %s | %s" % (hits[0]["title"], hits[0]["published"])) if hits else "NOT ON BOARD")
            continue
        if not hits:
            print("== %s: NOT FOUND\n" % want)
            continue
        p = hits[0]
        print("== %s | %s | %s | published %s%s | %s\n   %s" % (
            p["board"], p["title"], p["location"], p["published"],
            (", updated " + p["updated"]) if p["updated"] else "", p["pay"], p["url"]))
        if full:
            print(p["text"])
            print()
            continue
        lines = [l.strip() for l in p["text"].split("\n") if l.strip()]
        print("   SUMMARY:", " ".join(lines)[:420])
        shown = 0
        for l in lines:
            if REQUIRES.search(l) and len(l) > 12:
                print("   REQUIRES:", l[:260])
                shown += 1
                if shown >= 9:
                    break
        for l in [l for l in lines if PLACE.search(l)][:2]:
            print("   PLACE:", l[:200])
        stated = PAY.findall(p["text"])
        if stated and not p["pay"]:
            print("   PAY IN TEXT:", "; ".join(stated[:3]))
        print()


if __name__ == "__main__":
    main()
