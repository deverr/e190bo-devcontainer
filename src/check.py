"""Lab 5 self-check: is your API keeping the promises in CONTRACT.md?

Two terminals, both in src/:

    terminal 1:  uvicorn main:app --reload
    terminal 2:  python check.py

Each check sends a real request to your running server, the way a web page
would, and compares the answer with what the contract promises. It never
imports your code, so how you build the API is up to you.

Every FAIL says what to look at. Fix the first FAIL first: later checks often
fail because of an earlier one.

To check a server somewhere else:  API_URL=http://... python check.py
"""
import os
import sys
import uuid

import httpx

BASE = os.environ.get("API_URL", "http://localhost:8000")
# A fresh connection for every request: a server that just crashed (a 500)
# closes its connection, and reusing it would crash this script instead.
api = httpx.Client(base_url=BASE, timeout=10,
                   limits=httpx.Limits(max_keepalive_connections=0))
tag = uuid.uuid4().hex[:6]      # so each run's test ideas get new titles
failures = 0


def check(what, ok, hint=""):
    """Print one PASS or FAIL line. On a FAIL, also say what to look at."""
    global failures
    if ok:
        print("PASS", what)
    else:
        failures += 1
        print("FAIL", what)
        if hint:
            print("    ", hint)


def body(r):
    """The JSON a response sent back, or None if it didn't send any."""
    try:
        return r.json()
    except ValueError:
        return None


def id_of(r):
    """The id in a response like {"id": 3, ...}, or None."""
    b = body(r)
    return b.get("id") if isinstance(b, dict) else None


def listed(idea_id):
    """This idea's entry in GET /ideas, or None if it isn't there."""
    ideas = body(api.get("/ideas"))
    for i in ideas if isinstance(ideas, list) else []:
        if isinstance(i, dict) and i.get("id") == idea_id:
            return i
    return None


def crashed(r):
    """A hint for a 500, which always means the server's code raised an error."""
    if r.status_code == 500:
        return "got 500: your code crashed. The error is at the bottom of terminal 1."
    return ""


def why_not_422(r):
    """A hint for a bad request that wasn't rejected with a 422."""
    if r.status_code == 500:
        return ("got 500: a SQLModel class with table=True skips validation, so the bad "
                "body reached your database. Give the request body its own non-table "
                "class (the ⚠️ box in the handout).")
    if r.status_code < 300:
        return f"got {r.status_code}: you saved it anyway. Bad input should be refused."
    if r.status_code == 404:
        return "got 404: is this route there yet?"
    return f"got {r.status_code}."


try:
    api.get("/ideas")
except httpx.ConnectError:
    sys.exit(f"Can't reach your server at {BASE}.\n"
             "Start it in another terminal first:  uvicorn main:app --reload")


print("Contract: what Lab 6's page relies on. These have to pass.\n")

r = api.get("/ideas")
check("GET /ideas answers 200", r.status_code == 200,
      crashed(r) or f"got {r.status_code}. See CONTRACT.md §1.")
check("GET /ideas is a JSON list", isinstance(body(r), list),
      "see above." if r.status_code != 200 else
      'a list, not wrapped in an object like {"ideas": [...]}. See CONTRACT.md §1.')

title = f"Test idea {tag}"
r = api.post("/ideas", json={"title": title, "body": "from check.py"})
new_id = id_of(r)
check("POST /ideas succeeds", r.status_code < 300,
      crashed(r) or f"got {r.status_code}. See CONTRACT.md §2.")
check("POST /ideas returns the new idea's id", new_id is not None,
      "return the saved idea, with the id the database picked.")
check("POST /ideas returns the title you sent",
      isinstance(body(r), dict) and body(r).get("title") == title)

entry = listed(new_id)
check("the new idea is in GET /ideas", entry is not None,
      "Not committed? Or a plain JOIN against votes, which drops an idea with no "
      "votes: that's what LEFT JOIN is for.")
second_id = id_of(api.post("/ideas", json={"title": f"Another test idea {tag}"}))
ideas = body(api.get("/ideas"))
check("a second new idea is listed too", listed(second_id) is not None,
      "Only one idea came back at all: a COUNT without a GROUP BY collapses every "
      "row into one." if isinstance(ideas, list) and len(ideas) == 1 else "")
check("listed ideas have a whole-number vote_count",
      entry is not None and type(entry.get("vote_count")) is int,
      "every idea in GET /ideas needs a vote_count. See CONTRACT.md §1.")
check("a new idea is listed with vote_count 0",
      entry is not None and entry.get("vote_count") == 0,
      "no vote_count yet: see above." if entry is None or "vote_count" not in entry else
      "COUNT(*) after a LEFT JOIN counts the one row of NULLs the join made for "
      "it. Count a column from the vote table instead.")

r = api.get(f"/ideas/{new_id}")
one = body(r)
check("GET /ideas/{id} answers 200 with that idea",
      r.status_code == 200 and isinstance(one, dict) and one.get("title") == title,
      crashed(r) or f"got {r.status_code}. See CONTRACT.md §3.")
check("GET /ideas/{id} includes a votes list",
      isinstance(one, dict) and isinstance(one.get("votes"), list),
      "a `votes` key holding a JSON list, empty if nobody has voted. See CONTRACT.md §3.")

r = api.post(f"/ideas/{new_id}/vote", json={"voter": f"ada-{tag}"})
api.post(f"/ideas/{new_id}/vote", json={"voter": f"grace-{tag}"})
voted = r.status_code < 300
check("POST /ideas/{id}/vote succeeds", voted,
      crashed(r) or f"got {r.status_code}. See CONTRACT.md §4.")
one = body(api.get(f"/ideas/{new_id}"))
votes = one.get("votes") if isinstance(one, dict) else None
check("after two votes, its votes list has two",
      isinstance(votes, list) and len(votes) == 2,
      "voting doesn't work yet: see above." if not voted else
      "no votes list yet: see above." if not isinstance(votes, list) else
      f"it has {len(votes)}. The votes were saved but aren't all coming back: check "
      "the join on idea_id.")
entry = listed(new_id)
count = entry.get("vote_count") if entry else None
check("after two votes, its vote_count is 2", count == 2,
      "voting doesn't work yet: see above." if not voted else
      "no vote_count yet: see above." if count is None else
      f"got {count!r}. The total for every idea? Your count is missing a GROUP BY. "
      "Stuck at 0? Check the join matches votes to their idea.")


print("\nQuality: good API behaviour. Aim to pass all of these.\n")

r = api.post("/ideas", json={"title": f"Status {tag}"})
check("POST /ideas answers 201 Created", r.status_code == 201,
      f"got {r.status_code}. 201 is the honest answer when you made something: "
      "@app.post('/ideas', status_code=201)")
r2 = api.post("/ideas", json={"title": f"Second {tag}"})
check("two new ideas get different ids", None not in (id_of(r), id_of(r2))
      and id_of(r) != id_of(r2))

r = api.get("/ideas/99999999")
check("GET /ideas/{id} for a missing idea answers 404", r.status_code == 404,
      f"got {r.status_code}. An id that isn't there is a 404: not a 500, and not an "
      "empty 200.")
r = api.post("/ideas/99999999/vote", json={"voter": f"ghost-{tag}"})
check("voting on a missing idea answers 404", r.status_code == 404,
      f"got {r.status_code}. Check the idea exists before you save the vote.")

r = api.post("/ideas", json={"body": "no title here"})
check("POST /ideas with no title answers 422", r.status_code == 422, why_not_422(r))
r = api.post("/ideas", json={"title": {"not": "text"}})
check("POST /ideas with a title that isn't text answers 422", r.status_code == 422,
      why_not_422(r))
r = api.post(f"/ideas/{new_id}/vote", json={})
check("a vote with no voter answers 422", r.status_code == 422, why_not_422(r))
r = api.post(f"/ideas/{new_id}/vote", json={"voter": {"not": "text"}})
check("a vote whose voter isn't text answers 422", r.status_code == 422, why_not_422(r))


print()
if failures:
    print(f"{failures} FAIL. Start with the first one.")
else:
    print("Everything passes.")
sys.exit(1 if failures else 0)
