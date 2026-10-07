# The Ideas API contract

*Student-facing.
This is the promise your Lab 5 application programming interface (API) makes, and the only thing Lab 6 is allowed to assume.*

Everything **not** in this document is your call: framework, object-relational mapper (ORM), file layout, table names, extra endpoints, extra fields, how you validate, how you test.
Design it the way you want to defend at the check-in.

Run `python check.py` to check yourself against it.

---

## Why a contract exists at all

Lab 6 is a frontend for the API you build in Lab 5, and Lab 7 deploys both.
If every student's API were shaped differently, Lab 6's handout could only say "do whatever fits your thing," and nobody could help you debug it.

So a small number of shapes are fixed.
They're the ones a frontend actually touches.
Inside those, you have real latitude — and `check.py` is written to *stay out of your way*: it talks to your server over HTTP (Hypertext Transfer Protocol) and never imports your code, so a working Flask rewrite would pass just as well as FastAPI.

---

## §1 — `GET /ideas`

Returns **200** and a **JSON (JavaScript Object Notation) array** of ideas.
An empty board is `[]`, not `404` and not `null`.

```json
[
  { "id": 1, "title": "Sticker vending machine", "body": "...", "vote_count": 3 },
  { "id": 2, "title": "Bike lock that texts you", "body": "...", "vote_count": 0 }
]
```

Each element must have `id`, `title`, and **`vote_count`** — an integer, the number of votes that idea has.
Anything else you want to include is fine.

`vote_count` is the join across your two tables: the count lives in one table and the title in the other.
It is a `LEFT JOIN` with a `COUNT`, and it's what the check-in's SQL (Structured Query Language) question is about.
The list page in Lab 6 shows it, which is why it is here and not only on the detail endpoint.

> ⚠️ **An idea with no votes must still be in the list, with `vote_count: 0`.**
> A plain `JOIN` drops it — there is no vote row for it to match — so a brand new idea silently vanishes from the board.
> This is the `JOIN` vs `LEFT JOIN` question, and `check.py` checks it.

> ⚠️ A common miss: returning `{"ideas": [...]}`.
> That's a perfectly reasonable API design in general — lots of real APIs do it — but Lab 6's code will call `.map()` on the response, so for *this* contract it has to be the bare array.

## §2 — `POST /ideas`

Takes a JSON body with at least a `title`.
On success returns **201** and the **saved record, including the `id` your database assigned**.

> On the status code: `check.py`'s Contract checks accept any 2xx here, because a frontend checking `response.ok` can't tell the difference.
> Its Quality checks hold you to **201**, because you made something new and 201 is the honest way to say so.
> Both are deliberate — the Contract checks are the floor for Lab 6, the Quality checks are the standard for Lab 5.

```json
→ { "title": "Sticker vending machine", "body": "by the mailroom" }
← { "id": 7, "title": "Sticker vending machine", "body": "by the mailroom" }
```

The `id` matters: the frontend needs it to link to the thing it just created, and it can't know it in advance.
That's the whole reason the database assigns it rather than the client.

A body with **no title**, or a title that isn't a string, must be rejected with **422**.

## §3 — `GET /ideas/{id}`

Returns **200** and one idea, plus a **`votes` array**:

```json
{ "id": 7, "title": "...", "body": "...", "votes": [ { "voter": "ab" } ] }
```

`votes` holds that idea's rows from your votes table.
Including a `vote_count` here too is fine, and handy for Lab 6, but not required.

An `id` that doesn't exist returns **404**.

## §4 — `POST /ideas/{id}/vote`

Takes a JSON body with a `voter` (a string).
Records a vote on that idea and returns **201**.
Afterwards, the vote appears in §3's `votes` array, and that idea's `vote_count` in §1 has gone up by one.

A body with no `voter`, or a `voter` that isn't a string, must be rejected with **422**.

Voting on an idea that doesn't exist returns **404** — not 201, and not 500. The idea being absent is the client's mistake, not your server falling over.

---

## What the contract does *not* say

Genuinely up to you, and all good check-in material:

- Whether one voter can vote twice, and what you return if they try.
- Whether ideas can be edited or deleted, and at what URL (web address).
- Sorting, pagination, filtering.
  `GET /ideas?sort=votes` is a fine addition.
- How you compute `vote_count` — one query with a join, or something else.
  Both pass `check.py`.
  Only one of them survives a board with 1,000 ideas, and `echo=True` will show you which.
- What else is on an idea — author, timestamp, tags.
- Your table and column names, and whether you use an ORM at all.

If you add something, `check.py` won't know about it.
That's expected: **passing `check.py` is the floor, not the ceiling.**
It can't tell whether you understood any of it, which is what the check-in is for.

---

## Running `check.py`

Two terminals, both in `src/`.
Your server in one:

```bash
uvicorn main:app --reload
```

The checks in the other:

```bash
python check.py
```

It prints PASS or FAIL for each promise, and every FAIL says what to look at.
The **Contract** checks are §1–§4, the parts Lab 6 needs; the **Quality** checks are the 201s, 404s and 422s.

Point it somewhere else with `API_URL=https://your-app.up.railway.app python check.py`.

`check.py` writes real ideas into your database, with titles like `Test idea 4f2a9c`.
That's intentional: it runs against a real server, not a mock.
Delete `app.db` and restart if you want a clean board.
