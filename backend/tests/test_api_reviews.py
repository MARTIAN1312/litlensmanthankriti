"""Full pipeline through the HTTP API with fake LLM, arXiv and embeddings."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.ratelimit import ClientLimiter
from app.llm.prompts import synthesizer as synth_prompt
from app.main import create_app
from app.models.internal import Candidate
from tests.fakes import FakeArxiv, FakeProvider, candidate, make_services, make_settings

TOPIC = "crop disease detection"
CANDS = [
    candidate("2401.00001", "crop disease detection with deep CNN"),
    candidate("2401.00002", "crop disease detection using vision transformers"),
    candidate("2401.00003", "leaf disease crop detection dataset"),
    candidate("2401.00004", "detection of crop disease from drones"),
    candidate("2401.00005", "stock market prediction"),
]
REVIEW = "\n\n".join(
    f"## {s}\nCrop disease detection with deep CNN works well [1][2]. Ignored ref [42]."
    for s in synth_prompt.SECTIONS
)


class AnyQueryArxiv(FakeArxiv):
    async def search(self, query: str, max_results: int = 10) -> list[Candidate]:
        self.queries.append(query)
        return CANDS[:max_results]


def _extractions(refs: list[int]) -> str:
    return json.dumps(
        {
            "extractions": [
                {
                    "ref": r,
                    "problem": "crop disease",
                    "method": "deep CNN",
                    "datasets": ["PlantVillage"],
                    "metrics": [{"name": "Accuracy", "value": "97%"}],
                    "key_result": "high accuracy",
                    "limitations": "Not reported",
                }
                for r in refs
            ]
        }
    )


@pytest.fixture
def api(tmp_path: Path) -> Iterator[TestClient]:
    groq = FakeProvider(
        "groq",
        [
            json.dumps({"queries": ["crop disease CNN"]}),
            _extractions([1, 2, 3, 4]),
            REVIEW,
            "Deep CNNs detect crop disease well [1, p.1][2, p.1]. Invented [9, p.3].",
        ],
    )
    settings = make_settings(tmp_path)
    services = make_services(
        tmp_path, groq=groq, arxiv=AnyQueryArxiv(), settings=settings
    )
    with TestClient(create_app(settings, services)) as c:
        yield c


def _wait_done(c: TestClient, job_id: str) -> dict:
    for _ in range(200):
        body = c.get(f"/api/reviews/{job_id}").json()
        if body["status"] != "running":
            return body
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def _events(c: TestClient, job_id: str) -> list[dict]:
    out = []
    with c.stream("GET", f"/api/reviews/{job_id}/events") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            if line.startswith("data:"):
                out.append(json.loads(line[5:].strip()))
    return out


def test_full_review_flow(api: TestClient) -> None:
    r = api.post("/api/reviews", json={"topic": TOPIC, "max_papers": 4})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    assert r.json()["status"] == "queued"

    body = _wait_done(api, job_id)
    assert body["status"] == "done"
    assert [p["ref"] for p in body["papers"]] == [1, 2, 3, 4]
    assert "stock market" not in " ".join(p["title"] for p in body["papers"])
    assert len(body["extractions"]) == 4
    assert "[42]" not in body["review_md"]
    v = body["verification"]
    assert v["invalid_refs"] == [42] and v["citation_validity"] < 1
    assert body["stats"]["papers_considered"] == 5
    assert body["stats"]["papers_selected"] == 4
    assert set(body["stats"]["stage_ms"]) >= {"planning", "searching", "extracting"}
    assert body["stats"]["tokens"]["openai/gpt-oss-120b"] == 150

    events = _events(api, job_id)  # late subscriber: full history, then stream ends
    stages = [e["stage"] for e in events]
    for s in (
        "planning",
        "searching",
        "ranking",
        "extracting",
        "synthesizing",
        "verifying",
        "done",
    ):
        assert s in stages
    assert events[-1]["stage"] == "indexing" and events[-1]["status"] == "completed"
    assert "4 abstract only" in events[-1]["message"]  # fake fetcher has no PDFs
    after = api.get(f"/api/reviews/{job_id}").json()
    assert after["qa_ready"] is True
    assert {p["fulltext_status"] for p in after["papers"]} == {"abstract_only"}
    assert all(e["job_id"] == job_id for e in events)

    md = api.get(f"/api/reviews/{job_id}/export?format=md")
    assert md.status_code == 200
    assert md.headers["content-type"].startswith("text/markdown")
    assert (
        'filename="litlens-crop-disease-detection.md"'
        in md.headers["content-disposition"]
    )
    bib = api.get(f"/api/reviews/{job_id}/export?format=bib")
    assert bib.text.count("@misc{") == 4
    assert api.get(f"/api/reviews/{job_id}/export?format=pdf").status_code == 422


def test_result_survives_restart(tmp_path: Path, api: TestClient) -> None:
    job_id = api.post("/api/reviews", json={"topic": TOPIC, "max_papers": 4}).json()[
        "job_id"
    ]
    _events(api, job_id)  # wait until background indexing has finished
    settings = make_settings(tmp_path)
    fresh = make_services(tmp_path, settings=settings)  # new registry, same folder
    with TestClient(create_app(settings, fresh)) as c2:
        assert c2.get(f"/api/reviews/{job_id}").json()["status"] == "done"
        assert _events(c2, job_id)[-1]["stage"] == "indexing"


def test_ask_answers_with_valid_sources(api: TestClient) -> None:
    job_id = api.post("/api/reviews", json={"topic": TOPIC, "max_papers": 4}).json()[
        "job_id"
    ]
    _events(api, job_id)  # stream ends once indexing is done
    r = api.post(
        f"/api/reviews/{job_id}/ask", json={"question": "crop disease detection CNN?"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "[1, p.1]" in body["answer_md"] or "[2, p.1]" in body["answer_md"]
    assert "[9, p.3]" not in body["answer_md"]  # citation of a chunk not retrieved
    assert 1 <= len(body["sources"]) <= 4
    assert all(s["page"] == 1 and s["snippet"] for s in body["sources"])


def test_ask_before_ready_is_409(tmp_path: Path) -> None:
    from app.models.schemas import ReviewRequest

    settings = make_settings(tmp_path)
    services = make_services(tmp_path, settings=settings)
    job = services.jobs.create(ReviewRequest(topic=TOPIC))  # never run
    with TestClient(create_app(settings, services)) as c:
        r = c.post(f"/api/reviews/{job.id}/ask", json={"question": "which datasets?"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_READY"


@pytest.mark.parametrize("bad", ["nope", "../../etc/passwd", "123", "%2e%2e"])
def test_bad_job_ids_are_404(api: TestClient, bad: str) -> None:
    r = api.get(f"/api/reviews/{bad}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    assert (
        api.get("/api/reviews/9f1c2b7e-4a3d-4c1e-9b8a-2d6f5e7a1c30").status_code == 404
    )


def test_invalid_topic_rejected(api: TestClient) -> None:
    r = api.post("/api/reviews", json={"topic": "ab"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "topic" in r.json()["error"]["message"]


def test_rate_limit_on_create(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    groq = FakeProvider("groq", [])
    app = create_app(settings, make_services(tmp_path, groq=groq, settings=settings))
    app.state.client_limiter = ClientLimiter(per_minute=0)
    with TestClient(app) as c:
        r = c.post("/api/reviews", json={"topic": TOPIC})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_arxiv_down_gives_error_status(tmp_path: Path) -> None:
    down = FakeArxiv()
    down.fail = True
    groq = FakeProvider("groq", [json.dumps({"queries": ["x y"]})])
    settings = make_settings(tmp_path)
    app = create_app(
        settings, make_services(tmp_path, groq=groq, arxiv=down, settings=settings)
    )
    with TestClient(app) as c:
        job_id = c.post("/api/reviews", json={"topic": TOPIC}).json()["job_id"]
        body = _wait_done(c, job_id)
        assert body["status"] == "error" and body["warnings"]
        events = _events(c, job_id)
    assert events[-1]["stage"] == "error"


async def test_stream_keeps_events_published_during_history_replay() -> None:
    """Regression: a job finishing while a late subscriber replays history."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.models.schemas import ReviewRequest, ReviewResult, StageEvent
    from app.pipeline.jobs import Job

    jid = uuid4()
    job = Job(
        jid,
        ReviewRequest(topic=TOPIC),
        ReviewResult(
            job_id=jid, status="running", topic=TOPIC, created_at=datetime.now(UTC)
        ),
    )

    def ev(stage: str, status: str) -> StageEvent:
        return StageEvent(
            job_id=jid, stage=stage, status=status, message="m", elapsed_ms=0
        )

    await job.publish(ev("done", "completed"))
    stream = job.stream()
    first = await stream.__anext__()  # subscribed, replaying history...
    await job.publish(ev("indexing", "completed"))  # ...when the job finishes
    job.finish()
    rest = [e async for e in stream]
    assert (first.stage, [e.stage for e in rest]) == ("done", ["indexing"])


def test_demo_topics(api: TestClient) -> None:
    topics = api.get("/api/demo-topics").json()["topics"]
    assert 3 <= len(topics) <= 5
