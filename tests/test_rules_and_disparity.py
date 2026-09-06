"""Comprehensive unit and integration test suite for Developer 2:
Logic, Rules & Disparity Analytics Engine.

Runs offline without network access in < 1 second.
"""
import os
import json
import pytest

from carbon.schemas.contracts import (
    BoundingBox,
    RawSessionArtifacts,
    TelemetryData,
    ArtifactPaths,
    EvidenceRecord,
    EvidenceItem,
    DisparityItem,
    Severity,
)
from carbon.analyzers.text_analyzer import TextAnalyzer
from carbon.analyzers.vision_analyzer import VisionAnalyzer
from carbon.analyzers.a11y_analyzer import A11yAnalyzer
from carbon.rules.touch_target import TouchTargetSizeRule
from carbon.rules.spacing import InteractiveSpacingRule
from carbon.rules.contrast import ColorContrastRule
from carbon.rules.readability import ReadabilityRule, InclusiveLanguageRule
from carbon.rules.engine import RuleEngine
from carbon.disparity.metrics import (
    compute_disparity_ratio,
    compute_friction_score,
    compute_statistical_significance,
)
from carbon.disparity.engine import DisparityEngine
from carbon.evidence.store import EvidenceStore


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
DOM_SAMPLE_PATH = os.path.join(FIXTURES_DIR, "dom_sample.html")
SCREENSHOT_SAMPLE_PATH = os.path.join(FIXTURES_DIR, "screenshot_sample.png")
A11Y_TREE_SAMPLE_PATH = os.path.join(FIXTURES_DIR, "a11y_tree_sample.json")
RAW_SESSION_SAMPLE_PATH = os.path.join(FIXTURES_DIR, "raw_session_sample.json")


# ==============================================================================
# 1. Contract Schemas Tests
# ==============================================================================

def test_bounding_box_geometry():
    box1 = BoundingBox(x=10, y=10, width=50, height=50)
    box2 = BoundingBox(x=40, y=40, width=50, height=50)
    box3 = BoundingBox(x=100, y=10, width=50, height=50)

    assert box1.area == 2500.0
    assert box1.center == (35.0, 35.0)
    assert box1.overlaps(box2) is True
    assert box1.overlaps(box3) is False
    assert box1.edge_distance(box3) == 40.0  # 100 - (10 + 50) = 40


def test_contract_1_raw_session_serialization():
    with open(RAW_SESSION_SAMPLE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    session = RawSessionArtifacts(**data)
    assert session.session_id == "sess_12345"
    assert session.profile_id == "motor_impaired_keyboard_only"
    assert session.telemetry.completion_time_ms == 14200
    assert session.telemetry.task_completed is False
    assert session.telemetry.dead_clicks == 3


def test_contract_2_evidence_record_serialization():
    evidence_item = EvidenceItem(
        element_selector="button#submit-order",
        bounding_box=BoundingBox(x=120, y=450, width=24, height=22),
        rule_id="TOUCH_TARGET_TOO_SMALL",
        severity=Severity.CRITICAL,
        metric_value="24x22px",
        recommended_min="48x48px",
    )
    disparity_item = DisparityItem(
        metric="task_completion_rate",
        baseline_value=1.0,
        constrained_value=0.25,
        disparity_ratio=4.0,
        disadvantaged_group="motor_impaired",
    )

    record = EvidenceRecord(
        evidence=[evidence_item],
        disparities=[disparity_item],
    )

    dumped = record.model_dump()
    assert len(dumped["evidence"]) == 1
    assert dumped["evidence"][0]["rule_id"] == "TOUCH_TARGET_TOO_SMALL"
    assert dumped["evidence"][0]["severity"] == "CRITICAL"
    assert dumped["disparities"][0]["disparity_ratio"] == 4.0


# ==============================================================================
# 2. Multi-Modal Analyzers Tests
# ==============================================================================

def test_text_analyzer_readability_and_bias():
    with open(DOM_SAMPLE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    analyzer = TextAnalyzer()
    clean_text = analyzer.extract_clean_text_from_html(html)
    assert "Checkout Portal" in clean_text
    assert "<script>" not in clean_text

    result = analyzer.analyze_text(clean_text)
    assert result["word_count"] > 20
    assert result["sentence_count"] >= 3
    assert result["flesch_reading_ease"] < 80  # Has complex legal terms
    assert result["flesch_kincaid_grade"] > 5

    # Check biased terms flagged
    flagged = [item["term"] for item in result["flagged_terms"]]
    assert any("man hours" in t or "manpower" in t or "mankind" in t for t in flagged)


def test_vision_analyzer_contrast_and_screenshot():
    # 1. Contrast ratios
    # Pure black (#000000) on white (#FFFFFF) = 21:1
    ratio_bw = VisionAnalyzer.calculate_contrast_ratio((0, 0, 0), (255, 255, 255))
    assert ratio_bw >= 20.0

    # Low contrast gray (#999999) on white (#FFFFFF) ~ 2.84:1 -> Fails AA
    gray_rgb = VisionAnalyzer.parse_color_to_rgb("#999999")
    white_rgb = VisionAnalyzer.parse_color_to_rgb("#ffffff")
    ratio_gray = VisionAnalyzer.calculate_contrast_ratio(gray_rgb, white_rgb)
    assert ratio_gray < 4.5

    rule_res = VisionAnalyzer.evaluate_contrast_rule("#999999", "#ffffff", ".low-contrast-text")
    assert rule_res is not None
    assert rule_res.rule_id == "COLOR_CONTRAST_FAIL_AA"
    assert rule_res.severity == Severity.CRITICAL

    # 2. Screenshot analysis
    assert os.path.exists(SCREENSHOT_SAMPLE_PATH)
    screenshot_res = VisionAnalyzer.analyze_screenshot_image(SCREENSHOT_SAMPLE_PATH)
    assert screenshot_res["image_width"] == 800
    assert screenshot_res["image_height"] == 600
    assert screenshot_res["whitespace_ratio"] > 0.10
    assert 0.0 <= screenshot_res["clutter_score"] <= 1.0


def test_a11y_analyzer_html_checks():
    with open(DOM_SAMPLE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    findings = A11yAnalyzer.analyze_html(html)
    rule_ids = {f.rule_id for f in findings}

    # Missing alt attribute on img#product-hero
    assert "MISSING_ALT_TEXT" in rule_ids

    # Suspicious alt text on img#company-logo ("logo.png")
    assert "SUSPICIOUS_ALT_TEXT" in rule_ids

    # Unlabelled input #promo-code
    assert "UNLABELLED_FORM_INPUT" in rule_ids

    # Empty button #mystery-icon-btn
    assert "UNLABELLED_BUTTON" in rule_ids

    # Heading skipped: h1 directly to h3
    assert "HEADING_HIERARCHY_SKIPPED" in rule_ids

    # Inaccessible clickable div #fake-btn
    assert "INACCESSIBLE_CLICKABLE_ELEMENT" in rule_ids

    # Positive tabindex
    assert "POSITIVE_TABINDEX_DISCOURAGED" in rule_ids


def test_a11y_tree_analyzer():
    with open(A11Y_TREE_SAMPLE_PATH, "r", encoding="utf-8") as f:
        tree_data = json.load(f)

    tree_findings = A11yAnalyzer.analyze_a11y_tree_json(tree_data)
    assert len(tree_findings) >= 1
    assert any(item.rule_id == "AX_TREE_UNNAMED_INTERACTIVE_NODE" for item in tree_findings)


# ==============================================================================
# 3. Deterministic Rule Engine Tests
# ==============================================================================

def test_touch_target_rule():
    rule = TouchTargetSizeRule()
    context = {
        "interactive_elements": [
            {
                "selector": "button#submit-order",
                "bounding_box": {"x": 120, "y": 450, "width": 24, "height": 22},
            },
            {
                "selector": "button#large-btn",
                "bounding_box": {"x": 10, "y": 10, "width": 50, "height": 50},
            },
        ]
    }
    findings = rule.evaluate(context)
    assert len(findings) == 1
    assert findings[0].rule_id == "TOUCH_TARGET_TOO_SMALL"
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].metric_value == "24x22px"
    assert findings[0].recommended_min == "48x48px"


def test_interactive_spacing_rule():
    rule = InteractiveSpacingRule(min_spacing_px=8.0)
    context = {
        "interactive_elements": [
            {
                "selector": "button#ok",
                "bounding_box": {"x": 100, "y": 100, "width": 30, "height": 30},
            },
            {
                "selector": "button#cancel",
                "bounding_box": {"x": 132, "y": 100, "width": 30, "height": 30},  # 2px gap (132 - (100+30) = 2)
            },
        ]
    }
    findings = rule.evaluate(context)
    assert len(findings) == 1
    assert findings[0].rule_id == "INTERACTIVE_SPACING_TOO_TIGHT"
    assert findings[0].severity == Severity.WARNING
    assert "2.0px separation" in findings[0].metric_value


def test_rule_engine_full_evaluation():
    engine = RuleEngine()

    with open(DOM_SAMPLE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    context = {
        "html": html,
        "screenshot": SCREENSHOT_SAMPLE_PATH,
        "interactive_elements": [
            {
                "selector": "button#submit-order",
                "bounding_box": {"x": 120, "y": 450, "width": 24, "height": 22},
            },
            {
                "selector": "button#cancel-order",
                "bounding_box": {"x": 146, "y": 450, "width": 30, "height": 25},
            },
        ],
        "contrast_elements": [
            {
                "selector": ".low-contrast-text",
                "fg_color": "#999999",
                "bg_color": "#ffffff",
            }
        ],
    }

    evidence = engine.evaluate_context(context)
    assert len(evidence) >= 5

    # Check ordering: CRITICAL before WARNING before INFO
    severities = [item.severity for item in evidence]
    crit_indices = [i for i, s in enumerate(severities) if s == Severity.CRITICAL]
    warn_indices = [i for i, s in enumerate(severities) if s == Severity.WARNING]
    if crit_indices and warn_indices:
        assert max(crit_indices) < min(warn_indices)


# ==============================================================================
# 4. Disparity Engine Tests
# ==============================================================================

def test_disparity_math():
    # Completion rate disparity (higher is better): 1.0 vs 0.25 -> 4.0
    ratio_comp = compute_disparity_ratio(1.0, 0.25, higher_is_better=True)
    assert ratio_comp == 4.0

    # Duration disparity (higher is worse): 14200ms vs 3500ms -> 4.06
    ratio_time = compute_disparity_ratio(3500.0, 14200.0, higher_is_better=False)
    assert ratio_time == 4.06

    # Friction score
    tel_clean = TelemetryData(completion_time_ms=3500, task_completed=True, dead_clicks=0)
    score_clean = compute_friction_score(tel_clean)

    tel_impaired = TelemetryData(
        completion_time_ms=14200,
        task_completed=False,
        dead_clicks=3,
        missed_clicks=4,
        keyboard_nav_steps=24,
    )
    score_impaired = compute_friction_score(tel_impaired)

    assert score_clean < 10.0
    assert score_impaired > 60.0


def test_disparity_engine_session_comparison():
    engine = DisparityEngine()

    baseline = RawSessionArtifacts(
        session_id="sess_base",
        profile_id="baseline_default",
        url="https://example.com/checkout",
        artifacts=ArtifactPaths(),
        telemetry=TelemetryData(
            completion_time_ms=3500,
            task_completed=True,
            total_clicks=5,
            dead_clicks=0,
            keyboard_nav_steps=4,
        ),
    )

    motor_impaired = RawSessionArtifacts(
        session_id="sess_motor",
        profile_id="motor_impaired",
        url="https://example.com/checkout",
        artifacts=ArtifactPaths(),
        telemetry=TelemetryData(
            completion_time_ms=14200,
            task_completed=False,
            total_clicks=8,
            dead_clicks=3,
            missed_clicks=4,
            keyboard_nav_steps=24,
        ),
    )

    disparities = engine.analyze_sessions(baseline, [motor_impaired])
    metrics = {d.metric: d for d in disparities}

    assert "task_completion_rate" in metrics
    assert metrics["task_completion_rate"].disparity_ratio >= 4.0
    assert metrics["task_completion_rate"].disadvantaged_group == "motor_impaired"
    assert metrics["task_completion_rate"].severity == Severity.CRITICAL

    assert "completion_time_ms" in metrics
    assert metrics["completion_time_ms"].disparity_ratio >= 4.0

    assert "dead_clicks" in metrics
    assert metrics["dead_clicks"].disparity_ratio >= 3.0


# ==============================================================================
# 5. Evidence Store & Contract 2 Serialization
# ==============================================================================

def test_evidence_store_handoff(tmp_path):
    store = EvidenceStore()
    store.add_session_id("sess_12345")

    item1 = EvidenceItem(
        element_selector="button#submit-order",
        bounding_box=BoundingBox(x=120, y=450, width=24, height=22),
        rule_id="TOUCH_TARGET_TOO_SMALL",
        severity=Severity.CRITICAL,
        metric_value="24x22px",
        recommended_min="48x48px",
    )
    store.add_evidence(item1)

    disp1 = DisparityItem(
        metric="task_completion_rate",
        baseline_value=1.0,
        constrained_value=0.25,
        disparity_ratio=4.0,
        disadvantaged_group="motor_impaired",
    )
    store.add_disparity(disp1)

    payload = store.to_contract2_dict()
    assert "evidence" in payload
    assert "disparities" in payload
    assert payload["evidence"][0]["rule_id"] == "TOUCH_TARGET_TOO_SMALL"
    assert payload["disparities"][0]["disadvantaged_group"] == "motor_impaired"

    # Save to disk and reload
    out_file = str(tmp_path / "contract2_handoff.json")
    store.save_to_file(out_file)
    assert os.path.exists(out_file)

    loaded_store = EvidenceStore.load_from_file(out_file)
    assert len(loaded_store.evidence) == 1
    assert len(loaded_store.disparities) == 1
    assert loaded_store.evidence[0].element_selector == "button#submit-order"
    assert loaded_store.profiles_tested == []
    assert store.to_contract2_dict()["profiles_tested"] == []


# ==============================================================================
# 6. Bug Fixes & Edge Case Verifications
# ==============================================================================

def test_keyboard_nav_disparity_with_zero_baseline():
    """Verify keyboard disparity fires when baseline mouse user has 0 keyboard steps."""
    engine = DisparityEngine()
    baseline = RawSessionArtifacts(
        session_id="base_mouse",
        profile_id="baseline_default",
        url="https://example.com",
        artifacts=ArtifactPaths(),
        telemetry=TelemetryData(completion_time_ms=3000, task_completed=True, keyboard_nav_steps=0),
    )
    constrained = RawSessionArtifacts(
        session_id="constrained_kb",
        profile_id="keyboard_only_user",
        url="https://example.com",
        artifacts=ArtifactPaths(),
        telemetry=TelemetryData(completion_time_ms=7500, task_completed=True, keyboard_nav_steps=18),
    )

    disparities = engine.analyze_sessions(baseline, [constrained])
    kb_disp = next((d for d in disparities if d.metric == "keyboard_nav_steps"), None)
    assert kb_disp is not None
    assert kb_disp.disparity_ratio >= 18.0
    assert kb_disp.disadvantaged_group == "keyboard_only_user"


def test_robust_sentence_splitting():
    """Verify sentence splitter does not break on abbreviations or decimals."""
    analyzer = TextAnalyzer()
    sample = "Dr. Smith paid $19.99 for e.g. software. This is an awesome tool!"
    sentences = analyzer.split_sentences_robustly(sample)
    assert len(sentences) == 2
    assert "Dr. Smith paid $19.99 for e.g. software" in sentences[0]
    assert "This is an awesome tool" in sentences[1]


def test_nested_tags_no_duplicate_biased_findings():
    """Verify nested elements (div > p > span) only flag the innermost element once."""
    analyzer = TextAnalyzer()
    nested_html = """
    <div id="wrapper">
        <p id="container">
            <span id="target">We need more manpower here.</span>
        </p>
    </div>
    """
    evidence = analyzer.analyze_html_elements(nested_html)
    manpower_items = [e for e in evidence if "manpower" in e.metric_value]
    assert len(manpower_items) == 1
    # Only innermost tag (span) flagged
    assert manpower_items[0].element_selector == "span#target"


def test_grouped_controls_no_false_positive_overlap():
    """Verify intentionally adjacent buttons (segmented controls, button groups) are not flagged as overlap."""
    rule = InteractiveSpacingRule(min_spacing_px=8.0)
    context = {
        "interactive_elements": [
            {"selector": "tab1", "bounding_box": {"x": 0, "y": 0, "width": 40, "height": 30}, "group_id": "tabs"},
            {"selector": "tab2", "bounding_box": {"x": 40, "y": 0, "width": 40, "height": 30}, "group_id": "tabs"},
        ]
    }
    findings = rule.evaluate(context)
    assert len(findings) == 0


def test_evidence_item_profile_id_propagation():
    """Verify profile_id can be assigned and tracked on EvidenceItem."""
    item = EvidenceItem(
        element_selector="button#btn",
        rule_id="TOUCH_TARGET_TOO_SMALL",
        severity=Severity.CRITICAL,
        metric_value="20x20px",
        profile_id="motor_impaired",
    )
    assert item.profile_id == "motor_impaired"


def test_dev2_to_hydrogen_join_key_resolved():
    """Verify Dev 2 EvidenceRecord populates affected_profiles, enabling Hydrogen RESOLVED attribution."""
    import hydrogen

    rule_engine = RuleEngine()
    context = {
        "interactive_elements": [
            {"selector": "button#too-small", "bounding_box": {"x": 10, "y": 10, "width": 20, "height": 20}}
        ]
    }
    evidence = rule_engine.evaluate_context(context)
    assert len(evidence) == 1
    assert "motor_impaired" in evidence[0].affected_profiles

    store = EvidenceStore(
        evidence=evidence,
        disparities=[
            DisparityItem(
                metric="task_completion_rate",
                baseline_value=1.0,
                constrained_value=0.25,
                disparity_ratio=4.0,
                disadvantaged_group="motor_impaired",
            )
        ],
        target_url="https://example.com",
    )

    contract2_payload = store.to_contract2_dict()
    bundle = hydrogen.parse_contract2(contract2_payload)
    report = hydrogen.evaluate(bundle, report_id="rep_test_1")

    assert report.score_status == hydrogen.ScoreStatus.VALID
    assert report.overall_fairness_score is not None
    assert len(report.findings) == 1
    assert report.findings[0].attribution_status == hydrogen.AttributionStatus.RESOLVED
    assert "motor_impaired" in report.findings[0].affected_profiles


