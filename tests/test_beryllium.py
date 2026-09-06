"""Beryllium owns n_trials. Hydrogen never sees N. No live GPU."""

import pytest
from pydantic import BaseModel, ConfigDict, Field

import hydrogen
from beryllium.pipeline import (
    _aggregate_sessions,
    _host_evidence,
    _trial_frictions,
    run_pipeline,
)
from helium.client import MockLLMClient
from helium.example import example_bundle
from hydrogen.models import ScoreStatus


class _Tel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    completion_time_ms: int
    task_completed: bool
    total_clicks: int = 0
    dead_clicks: int = 0
    keyboard_nav_steps: int = 0
    missed_clicks: int = 0
    error_count: int = 0
    failed_selectors: list[str] = Field(default_factory=list)


class _Rec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    profile_id: str
    url: str = "https://example.com/checkout"
    artifacts: dict = Field(default_factory=dict)
    telemetry: _Tel


def _rec(profile_id, completed, session_id=None, **tel):
    tel.setdefault("completion_time_ms", 1000)
    return _Rec(
        session_id=session_id or f"s_{profile_id}",
        profile_id=profile_id,
        telemetry=_Tel(task_completed=completed, **tel),
    )


def test_aggregate_completion_rate_is_successes_over_n():
    records = [
        _rec("baseline_default", True, "b1", completion_time_ms=1000),
        _rec("baseline_default", True, "b2", completion_time_ms=2000),
        _rec("motor_impaired", True, "m1", completion_time_ms=3000),
        _rec("motor_impaired", False, "m2", completion_time_ms=4000),
        _rec("motor_impaired", False, "m3", completion_time_ms=5000),
    ]
    folded, rates = _aggregate_sessions(records)
    assert rates["baseline_default"] == 1.0
    assert rates["motor_impaired"] == pytest.approx(1 / 3)
    by_id = {row.profile_id: row for row in folded}
    assert by_id["baseline_default"].telemetry.completion_time_ms == 1500
    assert by_id["motor_impaired"].telemetry.completion_time_ms == 4000
    assert by_id["motor_impaired"].telemetry.task_completed is False
    frictions = _trial_frictions(records)
    assert frictions["motor_impaired"] < 40
    assert frictions["motor_impaired"] == pytest.approx(26.67, abs=0.01)


def test_host_evidence_uses_oxygen_and_fluorine(tmp_path):
    html = tmp_path / "dom.html"
    shot = tmp_path / "screenshot.png"
    html.write_text("<p>tiny pay</p>", encoding="utf-8")
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    rec = _rec("baseline_default", True)
    rec = rec.model_copy(
        update={"artifacts": {"html_path": str(html), "screenshot_path": str(shot)}}
    )

    class Text:
        def complete(self, system, user):
            return "Pay control is easy to miss."

    class Vision:
        def complete(self, system, user, image_b64=None):
            assert image_b64
            return "Primary button is undersized."

    items = _host_evidence([rec], "baseline_default", Text(), Vision())
    rules = {row["rule_id"] for row in items}
    assert "OXYGEN_PAGE_TEXT" in rules
    assert "FLUORINE_VIEW_FRICTION" in rules


def test_contract2_path_skips_capture(tmp_path, monkeypatch):
    path = tmp_path / "c2.json"
    path.write_text(example_bundle().model_dump_json(), encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise AssertionError("capture must not run")

    monkeypatch.setattr("beryllium.pipeline._capture", boom)
    report = run_pipeline("rep_c2", contract2_path=path, n_trials=7, diagnose=False)
    assert report.report_id == "rep_c2"
    assert report.overall_fairness_score == 72
    assert report.analyst == "hydrogen"
    assert report.diagnosis == ""


def test_n_trials_is_boron_runs_not_hydrogen(monkeypatch):
    seen = {}

    def fake_suite(**kwargs):
        seen["runs"] = kwargs["runs"]
        seen["prefix"] = kwargs["session_id_prefix"]
        return [
            _rec("baseline_default", True),
            _rec("keyboard_only", False),
        ]

    def fake_contract2(*_args, **_kwargs):
        return example_bundle().model_dump(mode="json")

    real_evaluate = hydrogen.evaluate
    evaluate_calls = []

    def wrapped(bundle, report_id):
        evaluate_calls.append((bundle, report_id))
        return real_evaluate(bundle, report_id)

    monkeypatch.setattr("beryllium.pipeline._run_suite", fake_suite)
    monkeypatch.setattr("beryllium.pipeline._build_contract2", fake_contract2)
    monkeypatch.setattr(hydrogen, "evaluate", wrapped)

    report = run_pipeline(
        "job_n",
        url="https://example.com/checkout",
        n_trials=3,
        success_selector="#done",
        steps=["#a"],
        profile_ids=["baseline_default", "keyboard_only"],
        diagnose=False,
    )
    assert seen["runs"] == 3
    assert seen["prefix"] == "job_n"
    assert evaluate_calls[0][1] == "job_n"
    dumped = evaluate_calls[0][0].model_dump()
    assert "n_trials" not in dumped
    assert report.overall_fairness_score == 72


def test_plan_failed_still_scores_the_planning_session(monkeypatch):
    from boron.runner import PlanFailed

    rec = _rec("baseline_default", False, "plan_base")
    events = []

    def fake_suite(**_kwargs):
        raise PlanFailed("activated nothing", records=[rec])

    def fake_contract2(folded, rates, frictions, **kwargs):
        assert [row.profile_id for row in folded] == ["baseline_default"]
        assert kwargs["profile_ids"] == ["baseline_default"]
        return example_bundle().model_dump(mode="json")

    monkeypatch.setattr("beryllium.pipeline._run_suite", fake_suite)
    monkeypatch.setattr("beryllium.pipeline._build_contract2", fake_contract2)
    report = run_pipeline(
        "job_plan",
        url="https://en.wikipedia.org",
        n_trials=1,
        success_selector="#x",
        goal="browse",
        plan_once=True,
        diagnose=False,
        on_progress=events.append,
    )
    assert report.analyst == "hydrogen"
    assert any(e.get("stage") == "plan_failed" for e in events)


def test_rejects_n_trials_below_one():
    with pytest.raises(ValueError, match="n_trials"):
        run_pipeline("x", url="https://example.com", n_trials=0, success_selector="#x")


def test_diagnose_through_pipeline(tmp_path):
    path = tmp_path / "c2.json"
    path.write_text(example_bundle().model_dump_json(), encoding="utf-8")
    client = MockLLMClient()
    report = run_pipeline(
        "rep_llm",
        contract2_path=path,
        diagnose=True,
        llm_client=client,
    )
    assert report.analyst == "helium"
    assert report.overall_fairness_score == 72
    assert report.score_status is ScoreStatus.VALID
    assert report.diagnosis.endswith(".")
    assert report.findings[0].diagnosis == ""
    assert client.last_user


def test_url_and_contract2_are_exclusive(tmp_path):
    path = tmp_path / "c2.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="not both"):
        run_pipeline("x", url="https://example.com", contract2_path=path)


def test_live_two_profile_pipeline(tmp_path):
    pytest.importorskip("playwright")
    pytest.importorskip("carbon")
    from pathlib import Path

    url = (Path(__file__).parent / "fixtures" / "test_page.html").resolve().as_uri()
    report = run_pipeline(
        "be_live",
        url=url,
        n_trials=1,
        profile_ids=["baseline_default", "keyboard_only"],
        steps=["#fake-button", "#submit-order"],
        success_selector="#order-confirmed",
        out_root=str(tmp_path),
        diagnose=False,
    )
    assert report.score_status is ScoreStatus.VALID
    assert report.analyst == "hydrogen"
    assert "keyboard_only" in report.profiles_tested
    assert report.overall_fairness_score is not None
