#!/usr/bin/env python3
"""Pull public job boards (Ashby, Greenhouse, Lever) and save every open posting in one shape.

Read-only. It asks each board's public endpoint for its list of jobs. It sends no personal data,
needs no account or key, and uses only the Python standard library.

Usage:  python3 pull_boards.py [boards.txt]
Writes: postings.jsonl next to this file, one posting per line.
"""
import concurrent.futures as cf
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (compatible; board-reader)"
SYSTEMS = ("ashby", "greenhouse", "lever")
WORKERS = 16


def get(url, timeout=45):
    """Fetch one public endpoint and return its JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def plain(markup):
    """Turn a posting's HTML into plain text, keeping line breaks and list items."""
    if not markup:
        return ""
    t = html.unescape(markup)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</div>|</h\d>", "\n", t)
    t = re.sub(r"(?i)<li[^>]*>", "- ", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t ]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def posting(system, board, **fields):
    """Every posting is saved with the same fields, whichever system it came from."""
    row = dict(system=system, board=board, id="", title="", location="", workplace="", published="",
               updated="", pay="", department="", url="", text="")
    row.update(fields)
    return row


def ashby(board):
    j = get("https://api.ashbyhq.com/posting-api/job-board/%s?includeCompensation=true" % urllib.parse.quote(board))
    rows = []
    for p in j.get("jobs", []):
        places = [p.get("location") or ""] + [s.get("location", "") for s in (p.get("secondaryLocations") or [])]
        comp = p.get("compensation") or {}
        rows.append(posting(
            "ashby", board, id=p.get("id") or "", title=p.get("title", ""),
            location="; ".join(x for x in places if x),
            workplace=p.get("workplaceType") or ("Remote" if p.get("isRemote") else ""),
            published=(p.get("publishedAt") or "")[:10],
            pay=comp.get("compensationTierSummary") or comp.get("scrapeableCompensationSalarySummary") or "",
            department=" / ".join(x for x in (p.get("department"), p.get("team")) if x),
            url=p.get("jobUrl", ""), text=p.get("descriptionPlain") or plain(p.get("descriptionHtml"))))
    return rows


def greenhouse(board):
    j = get("https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=true" % urllib.parse.quote(board), timeout=90)
    rows = []
    for p in j.get("jobs", []):
        rows.append(posting(
            "greenhouse", board, id=str(p.get("id")), title=p.get("title", ""),
            location=(p.get("location") or {}).get("name", ""),
            published=(p.get("first_published") or p.get("updated_at") or "")[:10],
            updated=(p.get("updated_at") or "")[:10],
            department=", ".join(d.get("name", "") for d in (p.get("departments") or [])),
            url=p.get("absolute_url", ""), text=plain(p.get("content"))))
    return rows


def lever(board):
    j = get("https://api.lever.co/v0/postings/%s?mode=json" % urllib.parse.quote(board))
    rows = []
    if not isinstance(j, list):
        return rows
    for p in j:
        cat = p.get("categories") or {}
        parts = [p.get("descriptionPlain") or ""]
        for section in p.get("lists") or []:
            parts.append((section.get("text") or "") + "\n" + plain(section.get("content")))
        parts.append(p.get("additionalPlain") or "")
        pay = p.get("salaryRange") or {}
        created = p.get("createdAt")
        rows.append(posting(
            "lever", board, id=p.get("id") or "", title=p.get("text", ""),
            location=cat.get("location", "") or "; ".join(cat.get("allLocations") or []),
            workplace=p.get("workplaceType") or "",
            published=time.strftime("%Y-%m-%d", time.gmtime(created / 1000)) if created else "",
            pay=("%s-%s %s/%s" % (pay.get("min"), pay.get("max"), pay.get("currency", ""), pay.get("interval", "")))
            if pay.get("min") else "",
            department=cat.get("team", "") or "", url=p.get("hostedUrl", ""), text="\n".join(parts)))
    return rows


FETCH = {"ashby": ashby, "greenhouse": greenhouse, "lever": lever}


def read_board_list(path):
    """One board per line. 'ashby:ramp' names the system; a bare name is tried on all three. '#' starts a comment.

    Returns the (system, board) pairs to fetch, and the set of bare names.
    """
    tasks, seen, bare = [], set(), set()
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        first, _, rest = line.partition(":")
        if rest:
            if first not in FETCH:
                raise SystemExit("%s: unknown system %r (use ashby, greenhouse or lever)" % (path, first))
            pairs = [(first, rest.strip())]
        else:
            bare.add(first)
            pairs = [(s, first) for s in SYSTEMS]
        for pair in pairs:
            if pair not in seen:
                seen.add(pair)
                tasks.append(pair)
    return tasks, bare


def try_board(task):
    system, board = task
    try:
        return system, board, FETCH[system](board), None
    except urllib.error.HTTPError as e:
        return system, board, None, "HTTP %s" % e.code
    except Exception as e:  # a timeout, a refused connection, a reply that is not JSON
        return system, board, None, type(e).__name__


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "boards.txt")
    tasks, bare = read_board_list(path)
    out = os.path.join(HERE, "postings.jsonl")
    answered, errors, total, started = [], {}, 0, time.time()
    with open(out, "w", encoding="utf-8") as f, cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for system, board, rows, err in pool.map(try_board, tasks):
            if rows is None:
                errors[(system, board)] = err
                continue
            if rows:
                answered.append((system, board, len(rows)))
                total += len(rows)
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
    found = {board for _, board, _ in answered}
    # A bare name is tried on three systems, so two misses are expected. It failed only if none answered.
    failed = sorted("%s:%s (%s)" % (s, b, e) for (s, b), e in errors.items() if b not in bare)
    failed += sorted("%s (on no system)" % b for b in bare if b not in found)
    print("%d boards answered with %d postings in %.0f seconds -> %s" % (
        len(answered), total, time.time() - started, os.path.basename(out)))
    for system, board, n in sorted(answered, key=lambda a: -a[2]):
        print("  %-10s %-24s %5d" % (system, board, n))
    if failed:
        print("did not answer:", ", ".join(failed))


if __name__ == "__main__":
    main()
