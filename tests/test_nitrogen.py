from nitrogen import VISION_MODEL, MockVLClient, ModalVLClient


def test_vision_model_is_qwen3_vl_30b():
    assert "Qwen3-VL-30B" in VISION_MODEL
    assert "VL" in VISION_MODEL


def test_mock_client_returns_raw_text():
    client = MockVLClient("ok")
    assert client.complete("sys", "look at this", image_b64="abc") == "ok"
    assert client.last_system == "sys"
    assert client.last_user == "look at this"
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
    assert seen == [("nitrogen_complete", ("s", "u", None))]


def test_nitrogen_init_does_not_import_hydrogen():
    import ast
    from pathlib import Path

    tree = ast.parse(Path("nitrogen/__init__.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("hydrogen")
            assert node.module != "helium.engine"
