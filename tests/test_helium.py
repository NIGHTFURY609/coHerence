import pytest

from helium import HELIUM_RUNTIME, REPORT_MODEL, diagnose, get_client
from helium.client import MockLLMClient, ModalLLMClient
from helium.example import example_bundle, example_report
from hydrogen.engine import evaluate
from helium.prompt import SYSTEM_PROMPT, user_prompt
from hydrogen.models import ScoreStatus


def _report():
    return example_report()


def test_report_model_is_qwen_27b_text():
    assert "27B" in REPORT_MODEL
    assert "VL" not in REPORT_MODEL


def test_runtime_default_is_ephemeral():
    assert HELIUM_RUNTIME == "ephemeral"


def test_helium_kv_cache_is_8_gib():
    from helium.constants import KV_CACHE_GIB, KV_CACHE_MEMORY_BYTES, MAX_NUM_SEQS

    assert KV_CACHE_GIB == 8
    assert KV_CACHE_MEMORY_BYTES == 8 * 1024**3
    assert MAX_NUM_SEQS == 8
    assert MAX_NUM_SEQS <= 167


def test_hydrogen_then_helium_locks_score():
    scored = evaluate(example_bundle(), "rep_example")
    assert scored.analyst == "hydrogen"
    assert scored.diagnosis == ""
    assert scored.overall_fairness_score == 72
    assert scored.breakdown.bottleneck_abs_gap == 0.28
    out = diagnose(scored, MockLLMClient())
    assert out.analyst == "helium"
    assert out.overall_fairness_score == 72
    assert out.score_status is ScoreStatus.VALID
    assert scored.analyst == "hydrogen"
    assert scored.diagnosis == ""


def test_diagnose_fills_synthesis_and_locks_score():
    src = _report()
    out = diagnose(src, MockLLMClient())
    assert out.analyst == "helium"
    assert "lower completion" in out.diagnosis.lower() or "substantially lower" in out.diagnosis
    assert "prominence" in out.remediation.lower() or "instruction" in out.remediation.lower()
    assert out.overall_fairness_score == 72
    assert out.score_status is ScoreStatus.VALID
    assert out.scoring_policy == "hydrogen-v1"
    assert out.breakdown.bottleneck_abs_gap == 0.28
    assert out.findings[0].diagnosis == ""
    assert src.diagnosis == ""
    assert src.analyst == "hydrogen"


def test_prompt_has_gap_and_findings_not_personas():
    client = MockLLMClient()
    diagnose(_report(), client)
    assert "28" in client.last_user
    assert "ambiguous" in client.last_user.lower()
    assert "prominence" in client.last_user.lower()
    assert "14" in client.last_user
    assert "button#submit-order" in client.last_user
    assert "#submit-help" in client.last_user
    assert "3 additional" in client.last_user.lower() or "additional errors" in client.last_user.lower()
    assert "find_1" not in client.last_user
    assert "overall_fairness_score" not in client.last_user
    assert "attribution_status" not in client.last_user
    assert "woman" not in SYSTEM_PROMPT.lower()
    assert "do not mention every row" in SYSTEM_PROMPT.lower()
    assert "unresolved" in SYSTEM_PROMPT.lower()


def test_user_prompt_matches_subarch_shape():
    text = user_prompt(_report())
    assert "Hydrogen:" in text
    assert "completion gap = 28 pp" in text
    assert "Interface:" in text
    assert "instruction is ambiguous" in text
    assert "primary action has low visual prominence" in text
    assert "keyboard navigation requires 14 steps" in text
    assert "button#submit-order" in text
    assert "#submit-help" in text
    assert "constrained profile made 3 additional errors" in text
    assert "find_1" not in text
    assert "RESOLVED" not in text


def test_system_prompt_is_not_page_specific():
    lower = SYSTEM_PROMPT.lower()
    assert "submit-order" not in lower
    assert "submit-help" not in lower
    assert "selector" in lower
    assert "user facts" in lower


def test_user_prompt_builder_sets_completion_gap_pp():
    text = user_prompt(_report())
    assert "completion gap = 28 pp" in text
    assert brief_gap_pp() == 28


def brief_gap_pp():
    from helium.prompt import brief

    return brief(_report())["hydrogen"]["completion_gap_pp"]


def test_empty_model_output_raises():
    class Empty:
        def complete(self, system: str, user: str):
            return None

    try:
        diagnose(_report(), Empty())
    except ValueError as exc:
        assert "JSON" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def helium_init_deps() -> set[str]:
    import ast
    from pathlib import Path

    tree = ast.parse(Path("helium/__init__.py").read_text())
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_helium_init_source_avoids_hydrogen():
    deps = helium_init_deps()
    assert "hydrogen" not in deps
    assert "hydrogen.models" not in deps
    assert "helium.engine" not in deps
    assert "helium.prompt" not in deps
    assert "helium.example" not in deps


def test_ephemeral_reuses_live_modal_run(monkeypatch):
    import sys
    import types

    import helium.runtime as rt

    class FakeApp:
        name = "coherence-helium"
        app_id = "ap-live"

    class FakeComplete:
        def remote(self, system: str, user: str) -> str:
            return '{"diagnosis":"d","remediation":"r"}'

    class FakeGPU:
        def __init__(self) -> None:
            self.complete = FakeComplete()

    live = types.ModuleType("helium_live_modal_run")
    live.app = FakeApp()
    live.HeliumGPU = FakeGPU
    monkeypatch.setitem(sys.modules, "helium_live_modal_run", live)

    def boom(*_a, **_k):
        raise AssertionError("must not import/start a second Modal app")

    monkeypatch.setattr(rt, "_deployed", boom)
    monkeypatch.delenv("HELIUM_RUNTIME", raising=False)
    assert rt.complete_on_gpu("sys", "usr") == '{"diagnosis":"d","remediation":"r"}'


def test_bad_json_raises():
    class Bad:
        def complete(self, system: str, user: str) -> str:
            return "not json"

    try:
        diagnose(_report(), Bad())
    except ValueError as exc:
        assert "JSON" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_truncated_remediation_is_rejected():
    class Cut:
        def complete(self, system: str, user: str) -> str:
            return (
                '{"diagnosis": "The constrained path has lower completion.",'
                ' "remediation": "Increase prominence of the"}'
            )

    try:
        diagnose(_report(), Cut())
    except ValueError as exc:
        assert "complete" in str(exc).lower()
    else:
        raise AssertionError("expected rejection of truncated remediation")


def test_missing_remediation_is_rejected():
    class Partial:
        def complete(self, system: str, user: str) -> str:
            return '{"diagnosis": "A 28 pp completion gap exists."}'

    try:
        diagnose(_report(), Partial())
    except Exception:
        return
    raise AssertionError("expected rejection when remediation is missing")


def test_system_prompt_forbids_causal_verbs():
    from helium.prompt import SYSTEM_PROMPT as prompt

    lower = prompt.lower()
    assert "driven by" in lower
    assert "correlates" in lower
    assert "do not say the ui facts caused" in lower


def test_think_tags_are_stripped():
    class Thinky:
        def complete(self, system: str, user: str) -> str:
            return (
                "<think>scratch</think>"
                '{"diagnosis": "A 28 pp completion gap was observed.",'
                ' "remediation": "Clarify the instruction."}'
            )

    out = diagnose(_report(), Thinky())
    assert "28" in out.diagnosis
    assert "instruction" in out.remediation.lower()
    assert "<think>" not in out.diagnosis


def test_diagnose_defaults_to_get_client(monkeypatch):
    fake = MockLLMClient()
    monkeypatch.setattr("helium.engine.get_client", lambda: fake)
    out = diagnose(_report())
    assert out.analyst == "helium"
    assert fake.last_user


def test_get_client_is_modal():
    assert isinstance(get_client(), ModalLLMClient)


def test_runtime_dispatch_ephemeral(monkeypatch):
    import helium.runtime as rt

    calls: list[str] = []
    monkeypatch.delenv("HELIUM_RUNTIME", raising=False)
    monkeypatch.setattr(rt, "_ephemeral", lambda method, *a: calls.append("ephemeral") or '{"ok":true}')
    monkeypatch.setattr(rt, "_deployed", lambda method, *a: calls.append("deployed") or '{"ok":false}')
    assert rt.complete_on_gpu("sys", "usr") == '{"ok":true}'
    assert calls == ["ephemeral"]


def test_runtime_dispatch_deployed_via_env(monkeypatch):
    import helium.runtime as rt

    calls: list[str] = []
    monkeypatch.setenv("HELIUM_RUNTIME", "deployed")
    monkeypatch.setattr(rt, "_ephemeral", lambda method, *a: calls.append("ephemeral") or '{"ok":false}')
    monkeypatch.setattr(rt, "_deployed", lambda method, *a: calls.append("deployed") or '{"ok":true}')
    assert rt.current_runtime() == "deployed"
    assert rt.complete_on_gpu("sys", "usr") == '{"ok":true}'
    assert calls == ["deployed"]


def test_modal_client_does_not_import_modal_until_complete(monkeypatch):
    client = ModalLLMClient()
    monkeypatch.setattr(
        "helium.runtime.complete_on_gpu",
        lambda system, user: '{"diagnosis":"d","remediation":"r"}',
    )
    assert client.complete("sys", "usr") == '{"diagnosis":"d","remediation":"r"}'


def test_modal_app_constants_match_package():
    pytest.importorskip("modal")
    import helium.modal_app as m
    from helium import constants as c

    assert m.REPORT_MODEL == c.REPORT_MODEL
    assert m.GPU == c.GPU
    assert m.GPU_MEMORY_UTILIZATION == c.GPU_MEMORY_UTILIZATION
    assert m.KV_CACHE_MEMORY_BYTES == c.KV_CACHE_MEMORY_BYTES
    assert m.KV_CACHE_GIB == 8
    assert m.MAX_NUM_SEQS == c.MAX_NUM_SEQS
    assert m.MAX_MODEL_LEN == c.MAX_MODEL_LEN
    assert m.MODAL_APP_NAME == c.MODAL_APP_NAME
    assert hasattr(m, c.HELIUM_CLS_NAME)
    assert "Qwen3-VL-30B" in m.NITROGEN_MODEL
    assert m.NITROGEN_GPU_MEMORY_UTILIZATION == c.NITROGEN_GPU_MEMORY_UTILIZATION
    assert m.NITROGEN_GPU_MEMORY_UTILIZATION < 0.77
