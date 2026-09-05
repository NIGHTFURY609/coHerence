from fluorine import VISION_MODEL, MockVLClient, ModalVLClient


def test_vision_model_is_gemma4_26b_a4b():
    assert "gemma-4-26B-A4B-it" in VISION_MODEL
    assert VISION_MODEL.startswith("google/")


def test_mock_client_returns_raw_text():
    client = MockVLClient("button is small")
    assert client.complete("sys", "look", image_b64="abc") == "button is small"
    assert client.last_image_b64 == "abc"


def test_modal_client_uses_shared_gpu(monkeypatch):
    import helium.runtime as rt

    seen: list[tuple] = []

    def fake_invoke(method, *args):
        seen.append((method, args))
        return "from-gpu"

    monkeypatch.setattr(rt, "invoke_gpu", fake_invoke)
    out = ModalVLClient().complete("s", "u", None)
    assert out == "from-gpu"
    assert seen == [("fluorine_complete", ("s", "u", None))]
