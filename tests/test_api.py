import json


def test_index_serves_chat_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Ask the Nestora docs" in res.text
    assert client.get("/static/app.js").status_code == 200


def test_health_reports_ready(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["ready"] is True
    assert data["chunks"] > 100
    assert "api_key" not in json.dumps(data).lower()


def test_documents_lists_knowledge_base(client):
    data = client.get("/api/documents").json()
    titles = {d["title"] for d in data["documents"]}
    assert "Plans and pricing" in titles
    assert data["total_chunks"] == sum(d["chunks"] for d in data["documents"])


def test_chat_json(client):
    res = client.post("/api/chat", json={"question": "What is the payout schedule for Starter?"})
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "Here is the answer [1]."
    assert body["sources"] and body["sources"][0]["id"] == 1


def test_chat_stream_is_server_sent_events(client):
    with client.stream("POST", "/api/chat/stream", json={"question": "How do I verify webhook signatures?"}) as res:
        assert res.headers["content-type"].startswith("text/event-stream")
        events = [json.loads(line[5:]) for line in res.iter_lines() if line.startswith("data:")]
    assert events[0]["type"] == "sources"
    assert events[-1]["type"] == "done"


def test_legacy_endpoint_still_works(client):
    res = client.post("/chat", json={"question": "What is Nestora?"})
    assert res.status_code == 200 and "answer" in res.json()


def test_rejects_empty_and_oversized_questions(client):
    assert client.post("/api/chat", json={"question": "   "}).status_code == 422
    assert client.post("/api/chat", json={"question": "x" * 5000}).status_code == 422
