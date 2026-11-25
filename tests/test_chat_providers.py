import json
import time
from email.utils import formatdate

import httpx
import numpy as np
import pytest

from app import db, jobs, provider_keys
from app.chat_provider import ChatProvider
from app.cloud import CloudRefusal


@pytest.fixture(autouse=True)
def clean_keys(monkeypatch):
    monkeypatch.setattr(provider_keys, "_session_keys", {})
    monkeypatch.setattr(provider_keys, "_cooldowns", {})
    for prefix in provider_keys.PREFIX.values():
        for suffix in ("KEY", "KEYS"):
            monkeypatch.delenv(f"{prefix}_API_{suffix}", raising=False)


@pytest.mark.parametrize("name,host", [("openrouter", "openrouter.ai"), ("nvidia", "integrate.api.nvidia.com")])
def test_select_model_and_fail_over(client, monkeypatch, name, host):
    field = f"{name}_model"
    assert client.put("/api/settings", json={"provider": name}).status_code == 422
    monkeypatch.setenv(provider_keys.PREFIX[name] + "_API_KEY", "key-one")
    settings = client.put("/api/settings", json={"provider": name, field: " other/chat:custom ",
                                                 "add_keys": "key-one, key-two"}).json()
    assert settings[field] == "other/chat:custom"
    assert "other/chat:custom" in settings["saved_models"][name]
    other = "nvidia" if name == "openrouter" else "openrouter"
    assert "other/chat:custom" not in settings["saved_models"][other]
    assert settings["key_counts"][name] == 2
    assert "key-one" not in str(settings) and "key-two" not in str(settings)
    assert client.put("/api/settings", json={"provider": "local"}).json()[field] == settings[field]
    assert client.put("/api/settings", json={"provider": name}).json()[field] == settings[field]
    assert client.put("/api/settings", json={field: "   "}).status_code == 422
    requests = []

    def respond(req):
        assert req.url.host == host
        body = json.loads(req.content)
        assert body["model"] == "other/chat:custom"
        parts = body["messages"][1]["content"]
        assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
        assert "local-name" not in req.content.decode()
        key = req.headers["authorization"]
        requests.append(key)
        if key == "Bearer key-one":
            return httpx.Response(429, headers={"Retry-After": "30"})
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": '{"text":"cerebellum","confidence":0.9}'}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        provider = ChatProvider(name, transport)
        for _ in range(2):
            assert provider.transcribe(np.zeros((4, 4), dtype=np.uint8),
                                       {"text": "Label this.", "student_name_local": "local-name"}) == ("cerebellum", .9)
    assert requests == ["Bearer key-one", "Bearer key-two", "Bearer key-two"]


def test_pool_exhaustion_and_recovery(monkeypatch):
    now = time.time()
    monkeypatch.setattr(provider_keys.time, "time", lambda: now)
    provider_keys.add_keys("nvidia", ["one", "two"])
    provider_keys.cool_down("nvidia", "one", formatdate(now + 120, usegmt=True))
    provider_keys.cool_down("nvidia", "two", None)
    with pytest.raises(provider_keys.PoolLimited) as exc:
        provider_keys.next_key("nvidia", set())
    assert exc.value.seconds == 60
    provider_keys.add_keys("openrouter", ["one"])
    assert provider_keys.next_key("openrouter", set()) == "one"
    now += 61
    assert provider_keys.next_key("nvidia", set()) == "two"


def test_report_tasks_use_question_and_topic_data_only(data):
    db.init()
    provider_keys.add_keys("nvidia", ["one"])
    outputs = iter([{"mappings": [{"number": 1, "topic_code": "A", "confidence": .8}]},
                    {"keys": [{"number": 1, "answer": "B"}]},
                    {"topics": [{"code": "A", "activities": ["Draw a neuron."]}]}])

    def respond(req):
        content = json.loads(req.content)["messages"][1]["content"]
        assert isinstance(content, str) and "private student response" not in content
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(next(outputs))}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        provider = ChatProvider("nvidia", transport)
        questions = [{"number": 1, "text": "Name the cell.", "type": "mcq"}]
        topics = [{"code": "A", "title": "Neurons", "description": "Cells", "miss_rate": .8}]
        assert provider.map_topics(questions, topics) == {1: ("A", .8)}
        assert provider.derive_answers(questions, {1: ["private student response"]}) == {1: "B"}
        assert provider.reteach(topics) == {"A": ["Draw a neuron."]}


def test_auth_errors_do_not_cycle_keys(data):
    db.init()
    provider_keys.add_keys("nvidia", ["one", "two"])
    seen = []

    def reject(req):
        seen.append(req.headers["Authorization"])
        return httpx.Response(401)

    with httpx.Client(transport=httpx.MockTransport(reject)) as transport:
        with pytest.raises(CloudRefusal, match="401"):
            ChatProvider("nvidia", transport).reteach([])
    assert seen == ["Bearer one"]


def test_quota_wait_preserves_job(data, monkeypatch):
    db.init()
    def limited(c, job):
        raise provider_keys.PoolLimited("nvidia", time.time() + 120)
    monkeypatch.setitem(jobs.STAGES, "quota", limited)
    with db.connect() as c:
        jobs.enqueue(c, "quota")
        assert jobs.run_one(c)
        assert tuple(c.execute("SELECT status, attempts FROM job").fetchone()) == ("queued", 0)
        assert not jobs.run_one(c)
        c.execute("UPDATE job SET not_before=1")
        monkeypatch.setitem(jobs.STAGES, "quota", lambda c, job: None)
        assert jobs.run_one(c)
        assert c.execute("SELECT status FROM job").fetchone()[0] == "done"
