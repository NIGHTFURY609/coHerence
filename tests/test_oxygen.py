import json

from oxygen import GPU_TEXT_MODEL, TEXT_MODEL, GpuTextClient, GroqTextClient, MockTextClient, get_client


def test_text_model_is_gpt_oss_20b():
    assert TEXT_MODEL == "openai/gpt-oss-20b"


def test_gpu_text_model_is_qwen_9b():
    assert "9B" in GPU_TEXT_MODEL
    assert GPU_TEXT_MODEL.startswith("Qwen/")


def test_get_client_is_gpu():
    assert isinstance(get_client(), GpuTextClient)


def test_gpu_client_uses_shared_replica(monkeypatch):
    import helium.runtime as rt

    seen: list[tuple] = []

    def fake_invoke(method, *args):
        seen.append((method, args))
        return "from-gpu"

    monkeypatch.setattr(rt, "invoke_gpu", fake_invoke)
    assert GpuTextClient().complete("s", "u") == "from-gpu"
    assert seen == [("oxygen_complete", ("s", "u"))]


def test_mock_client_returns_raw_text():
    client = MockTextClient("clear the label")
    assert client.complete("sys", "this button is confusing") == "clear the label"
    assert client.last_user == "this button is confusing"


def test_groq_client_requires_env(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    try:
        GroqTextClient().complete("s", "u")
    except RuntimeError as exc:
        assert "GROQ_API_KEY" in str(exc)
    else:
        raise AssertionError("expected missing key error")


def test_groq_client_posts_model_and_messages(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_not_real")
    seen: dict = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "  rewrite the CTA  "}}]}
            ).encode()

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        seen["auth"] = req.headers.get("Authorization") or req.get_header("Authorization")
        seen["body"] = json.loads(req.data.decode())
        return FakeResp()

    monkeypatch.setattr("oxygen.client.urllib.request.urlopen", fake_urlopen)
    out = GroqTextClient().complete("be precise", "is this instruction ambiguous?")
    assert out == "rewrite the CTA"
    assert seen["url"].endswith("/chat/completions")
    assert seen["auth"] == "Bearer gsk_test_not_real"
    assert seen["body"]["model"] == "openai/gpt-oss-20b"
    assert seen["body"]["messages"][0]["content"] == "be precise"
    assert "ambiguous" in seen["body"]["messages"][1]["content"]
