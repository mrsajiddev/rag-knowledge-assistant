from app.db.vector_store import Hit
from app.providers.llm import ThinkFilter
from app.rag.pipeline import rerank


def test_retrieves_the_right_document(pipeline):
    sources = pipeline.retrieve("What does error NS-4012 COD limit exceeded mean?")
    assert sources, "expected at least one passage"
    assert sources[0].source == "11-error-codes.md"
    assert "150,000" in sources[0].text


def test_retrieves_handbook_policy(pipeline):
    sources = pipeline.retrieve("How many days of annual leave do employees get?")
    assert any(s.source == "internal/16-employee-handbook.md" for s in sources)


def test_follow_up_uses_previous_question(pipeline):
    history = [{"role": "user", "content": "What is the webhook retry schedule?"},
               {"role": "assistant", "content": "Up to 8 retries [1]."}]
    sources = pipeline.retrieve("and how long do I have to respond?", history)
    assert any(s.source == "09-webhooks.md" for s in sources)


def test_rerank_boosts_exact_error_codes():
    a = Hit("a", 0.50, {"title": "Shipping", "section": "", "text": "Couriers deliver parcels."})
    b = Hit("b", 0.30, {"title": "Errors", "section": "NS-4002", "text": "Pickup cut-off missed."})
    ranked = rerank("what is NS-4002", [a, b], min_score=0.35, top_k=5)
    assert ranked[0].id == "b"  # kept despite low score, and boosted to the top


def test_rerank_drops_weak_hits():
    weak = Hit("w", 0.1, {"title": "", "section": "", "text": "unrelated"})
    assert rerank("pricing", [weak], min_score=0.35, top_k=5) == []


def test_stream_emits_sources_tokens_done_and_strips_thinking(pipeline):
    events = list(pipeline.stream("How much does the Growth plan cost per month?"))
    kinds = [e["type"] for e in events]
    assert kinds[0] == "sources" and kinds[-1] == "done" and "token" in kinds
    text = "".join(e["text"] for e in events if e["type"] == "token")
    assert text == "Here is the answer [1]."
    system = pipeline.llm.last_messages[0]["content"]
    assert "[1]" in system and "Nestora" in system


def test_think_filter_handles_split_tags():
    f = ThinkFilter()
    parts = ["<thi", "nk>secret", " stuff</th", "ink>\n\nVisible", " text"]
    assert "".join(f.feed(p) for p in parts) + f.flush() == "Visible text"
