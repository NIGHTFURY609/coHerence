"""Multi-modal artifact capture. DOM, screenshot, a11y tree, element geometry."""

from __future__ import annotations

import base64
import json
from pathlib import Path

DOM_FILENAME = "dom.html"
SCREENSHOT_FILENAME = "screenshot.png"
A11Y_TREE_FILENAME = "a11y_tree.json"
ELEMENTS_FILENAME = "elements.json"

# Interactive and text-bearing elements. Dev 2's rules only apply to these.
CAPTURED_SELECTOR = (
    "a, button, input, select, textarea, label, img, "
    "h1, h2, h3, h4, h5, h6, p, li, [role], [onclick]"
)

# One definition, used by both the element dump and the runner, so a selector
# recorded in failed_selectors matches an elements.json selector exactly.
_CSS_PATH_JS = r"""
  const cssPath = (el) => {
    if (el.id) return el.tagName.toLowerCase() + '#' + el.id;
    const parts = [];
    while (el && el.nodeType === 1 && parts.length < 5) {
      let part = el.tagName.toLowerCase();
      const parent = el.parentElement;
      if (el.id) { parts.unshift(part + '#' + el.id); break; }
      if (parent) {
        const sibs = [...parent.children].filter(c => c.tagName === el.tagName);
        if (sibs.length > 1) part += ':nth-of-type(' + (sibs.indexOf(el) + 1) + ')';
      }
      parts.unshift(part);
      el = parent;
    }
    return parts.join(' > ');
  };
"""

CANONICAL_SELECTOR_SCRIPT = (
    "(sel) => { " + _CSS_PATH_JS + " const el = document.querySelector(sel);"
    " return el ? cssPath(el) : sel; }"
)

_ELEMENT_SCRIPT = r"""
(selector) => {
""" + _CSS_PATH_JS + r"""
  // Computed transparent is 'rgba(r, g, b, 0)'.
  const opaque = (c) => !!c && c !== 'transparent' && !c.endsWith(', 0)');
  // Contrast is against what is actually painted behind the text, not the
  // element's own background, which is transparent for most elements.
  const effectiveBackground = (el) => {
    for (let node = el; node; node = node.parentElement) {
      const c = getComputedStyle(node).backgroundColor;
      if (opaque(c)) return c;
    }
    return 'rgb(255, 255, 255)';
  };
  const INTERACTIVE = ['a', 'button', 'input', 'select', 'textarea'];
  return [...document.querySelectorAll(selector)].map((el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    const tag = el.tagName.toLowerCase();
    return {
      element_selector: cssPath(el),
      tag: tag,
      interactive: INTERACTIVE.includes(tag)
        || el.hasAttribute('onclick')
        || el.hasAttribute('role')
        || el.tabIndex >= 0,
      bounding_box: { x: r.x, y: r.y, width: r.width, height: r.height },
      font_size: s.fontSize,
      font_weight: s.fontWeight,
      line_height: s.lineHeight,
      text: (el.textContent || '').trim().slice(0, 200),
      color: s.color,
      background_color: effectiveBackground(el),
      alt: el.getAttribute('alt'),
      aria_label: el.getAttribute('aria-label'),
      tabindex: el.getAttribute('tabindex'),
      visible: r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none',
    };
  });
}
"""


def capture_artifacts(page, out_dir: Path) -> dict[str, str]:
    """Write the four artifacts. Returns POSIX paths keyed for SessionArtifacts."""
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / DOM_FILENAME).write_text(page.content(), encoding="utf-8")
    page.screenshot(path=str(out_dir / SCREENSHOT_FILENAME), full_page=True)

    cdp = page.context.new_cdp_session(page)
    try:
        tree = cdp.send("Accessibility.getFullAXTree")
    finally:
        cdp.detach()
    _write_json(out_dir / A11Y_TREE_FILENAME, tree)

    elements = page.evaluate(_ELEMENT_SCRIPT, CAPTURED_SELECTOR)
    _write_json(out_dir / ELEMENTS_FILENAME, elements)

    return {
        "html_path": _posix(out_dir / DOM_FILENAME),
        "screenshot_path": _posix(out_dir / SCREENSHOT_FILENAME),
        "a11y_tree_path": _posix(out_dir / A11Y_TREE_FILENAME),
        "elements_path": _posix(out_dir / ELEMENTS_FILENAME),
    }


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _posix(path: Path) -> str:
    return path.as_posix()


def viewport_screenshot_b64(page) -> tuple[str, int, int]:
    """Base64 PNG of the viewport, with the pixel size the model will see.

    Navigation needs the viewport, not the full page: the model answers in the
    coordinate space of the image it was given, and page.mouse works in viewport
    CSS px. Zoomed profiles need no correction -- document.body.style.zoom scales
    content inside the same viewport, so the shot is already what that user sees.
    """
    png = page.screenshot(full_page=False)
    return base64.b64encode(png).decode("ascii"), *_png_size(png)


def _png_size(png: bytes) -> tuple[int, int]:
    """Width and height from the IHDR chunk.

    Read from the image rather than from `page.viewport_size`: the two diverge
    as soon as device_scale_factor is not 1, and the model is told these numbers
    and answers in them. Guessing wrong would silently halve every coordinate.
    """
    if len(png) < 24 or png[1:4] != b"PNG":
        raise ValueError("screenshot is not a PNG")
    return (
        int.from_bytes(png[16:20], "big"),
        int.from_bytes(png[20:24], "big"),
    )


ELEMENT_AT_POINT_SCRIPT = (
    "([x, y]) => { " + _CSS_PATH_JS + " const el = document.elementFromPoint(x, y);"
    " return el ? cssPath(el) : null; }"
)


def element_at_point(page, x: float, y: float) -> str | None:
    """elements.json selector under a point, or None.

    A coordinate click has no selector of its own, so this is what keeps
    Telemetry.failed_selectors in the form carbon's join expects.
    """
    try:
        return page.evaluate(ELEMENT_AT_POINT_SCRIPT, [x, y])
    except Exception:
        return None


def focusable_ax_text(page, limit: int = 60) -> str:
    """Focusable a11y nodes as numbered lines, for a user who cannot see the page."""
    cdp = page.context.new_cdp_session(page)
    try:
        tree = cdp.send("Accessibility.getFullAXTree")
    finally:
        cdp.detach()

    lines = []
    for node in tree.get("nodes", []):
        if node.get("ignored"):
            continue
        role = (node.get("role") or {}).get("value") or ""
        name = ((node.get("name") or {}).get("value") or "").strip()
        if not name or role in _UNNAMED_ROLES:
            continue
        lines.append(f"{len(lines) + 1}. {role} '{name}'")
        if len(lines) >= limit:
            break
    return "\n".join(lines)


# Structural roles carry no interaction affordance; listing them buries the rest.
_UNNAMED_ROLES = frozenset(
    {"RootWebArea", "generic", "none", "presentation", "StaticText", "InlineTextBox"}
)
