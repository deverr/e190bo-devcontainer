from fastapi import FastAPI, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, func, select

app = FastAPI()

engine = create_engine("sqlite:///app.db", echo=True)


# ---- Tables ----

class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    body: str = ""


class Vote(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    idea_id: int = Field(foreign_key="idea.id")
    voter: str


# ---- Request bodies (no table=True, so FastAPI validates them -> 422) ----

class IdeaCreate(SQLModel):
    title: str
    body: str = ""


class VoteCreate(SQLModel):
    voter: str


SQLModel.metadata.create_all(engine)


# ---- Routes ----

@app.get("/ideas")
def list_ideas():
    # LEFT JOIN keeps ideas with no votes; counting Vote.id (not *) makes
    # those ideas show 0; GROUP BY gives one row per idea.
    stmt = (
        select(Idea, func.count(Vote.id))
        .join(Vote, isouter=True)
        .group_by(Idea.id)
    )
    with Session(engine) as s:
        rows = s.exec(stmt).all()
    return [{**idea.model_dump(), "vote_count": n} for idea, n in rows]


@app.post("/ideas", status_code=201)
def create_idea(payload: IdeaCreate):
    idea = Idea(title=payload.title, body=payload.body)
    with Session(engine) as s:
        s.add(idea)
        s.commit()
        s.refresh(idea)  # fills in the id the database picked
        return idea


@app.get("/ideas/{idea_id}")
def get_idea(idea_id: int):
    with Session(engine) as s:
        idea = s.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(404, "no such idea")
        votes = s.exec(select(Vote).where(Vote.idea_id == idea_id)).all()
    return {
        **idea.model_dump(),
        "vote_count": len(votes),
        "votes": [v.model_dump() for v in votes],
    }


@app.post("/ideas/{idea_id}/vote", status_code=201)
def vote_for_idea(idea_id: int, payload: VoteCreate):
    with Session(engine) as s:
        if s.get(Idea, idea_id) is None:
            raise HTTPException(404, "no such idea")
        vote = Vote(idea_id=idea_id, voter=payload.voter)
        s.add(vote)
        s.commit()
        s.refresh(vote)
        return vote
