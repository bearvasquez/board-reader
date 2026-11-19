# board-reader

Reads the public job boards that companies host on Ashby, Greenhouse and Lever, and saves every open posting in one file, with the same fields for each.

A company's job board is a small public data source. It says what the company is hiring for, where, at what pay, and since when. Each of the three systems publishes its boards through an open endpoint, and each uses its own format. This tool pulls any list of boards in parallel and writes them in one shape, so a person or an agent can search them together.

## What is here

| File | What it does |
|---|---|
| `pull_boards.py` | Asks each board in `boards.txt` for its open postings and writes them to `postings.jsonl`, one per line |
| `find_postings.py` | Lists saved postings whose title matches a pattern, with optional date and place filters |
| `read_posting.py` | Prints one posting's summary and the lines that state requirements, place and pay |
| `boards.txt` | The boards to pull. A few public ones are there to start |

It only reads. It calls three public endpoints, sends no personal data, and needs no account or key. It uses only the Python standard library, so there is nothing to install.

## Run it

```bash
python3 pull_boards.py
python3 find_postings.py "partnership|licensing" --since 2026-10-01 --place "san francisco|remote"
python3 read_posting.py ramp:cc0af88a
```

The first command writes `postings.jsonl` beside the scripts. On 2026-11-18 the nine boards in `boards.txt` returned 1,574 postings in six seconds.

Each saved posting has the same twelve fields: `system`, `board`, `id`, `title`, `location`, `workplace`, `published`, `updated`, `pay`, `department`, `url` and `text`.

In `boards.txt`, a line such as `ashby:ramp` names the system. A bare name is tried on all three. The finder prints each posting's short address (`ramp:cc0af88a`), which is what the reader takes.

## What it does not cover

- Employers that run their own careers sites, or use Workday.
- Application forms.
- Pay, where a board leaves it out of its structured fields. The finder and the reader then look for a range in the posting's text.
- A board name can belong to a different company than you expect. Check the link.

## Who did what

I set the question this tool answers. Claude Code, an AI coding agent, wrote the code in my working session, and this public copy is a trimmed version of it. I run it and act on what it returns. The version I use reads about 290 boards and returns roughly 23,500 postings in a minute or two.
