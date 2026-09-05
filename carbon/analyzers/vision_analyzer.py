"""Vision analyzer for visual density, clutter scoring, whitespace ratio, and WCAG contrast ratio validation."""
from __future__ import annotations
import math
import re
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
from PIL import Image

from carbon.schemas.contracts import EvidenceItem, Severity, BoundingBox


# Basic CSS Color name mapping for common web colors
NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "silver": (192, 192, 192),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "lightgray": (211, 211, 211),
    "lightgrey": (211, 211, 211),
    "darkgray": (169, 169, 169),
    "darkgrey": (169, 169, 169),
    "transparent": (255, 255, 255),  # Assume white page default if transparent
}


class VisionAnalyzer:
    """Multi-modal vision analyzer analyzing visual aesthetics, density, clutter, and contrast ratios.
    
    Caveat: For transparent backgrounds and 8-bit alpha channels, an opaque background
    (default white #FFFFFF, or customizable for dark-mode pages) is assumed for composite blending.
    """

    @staticmethod
    def parse_color_to_rgb(
        color_str: str,
        default_bg_rgb: Tuple[int, int, int] = (255, 255, 255),
    ) -> Optional[Tuple[int, int, int]]:
        """Parse hex, rgb(), rgba(), or named color strings into (R, G, B) integer tuple."""
        if not color_str:
            return None
        c = color_str.strip().lower()

        if c == "transparent":
            return default_bg_rgb

        if c in NAMED_COLORS:
            return NAMED_COLORS[c]

        # Hex code: #RGB or #RRGGBB
        if c.startswith("#"):
            hex_body = c[1:]
            if len(hex_body) == 3:
                return (
                    int(hex_body[0] * 2, 16),
                    int(hex_body[1] * 2, 16),
                    int(hex_body[2] * 2, 16),
                )
            if len(hex_body) == 6:
                return (
                    int(hex_body[0:2], 16),
                    int(hex_body[2:4], 16),
                    int(hex_body[4:6], 16),
                )
            if len(hex_body) == 8:  # RGBA hex
                return (
                    int(hex_body[0:2], 16),
                    int(hex_body[2:4], 16),
                    int(hex_body[4:6], 16),
                )

        # rgb(r, g, b) or rgba(r, g, b, a)
        rgb_match = re.match(r"rgba?\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", c)
        if rgb_match:
            r = min(255, max(0, int(rgb_match.group(1))))
            g = min(255, max(0, int(rgb_match.group(2))))
            b = min(255, max(0, int(rgb_match.group(3))))
            return (r, g, b)

        return None

    @staticmethod
    def calculate_relative_luminance(rgb: Tuple[int, int, int]) -> float:
        """Calculate WCAG 2.1 relative luminance for an sRGB color.
        
        Formula:
            L = 0.2126 * R' + 0.7152 * G' + 0.0722 * B'
            where C' = C/255 <= 0.04045 ? C/255 / 12.92 : ((C/255 + 0.055) / 1.055) ** 2.4
        """
        def channel_lum(val: int) -> float:
            c = val / 255.0
            return c / 12.92 if c <= 0.04045 else math.pow((c + 0.055) / 1.055, 2.4)

        r_lum = channel_lum(rgb[0])
        g_lum = channel_lum(rgb[1])
        b_lum = channel_lum(rgb[2])

        return 0.2126 * r_lum + 0.7152 * g_lum + 0.0722 * b_lum

    @classmethod
    def calculate_contrast_ratio(
        cls,
        fg_rgb: Tuple[int, int, int],
        bg_rgb: Tuple[int, int, int],
    ) -> float:
        """Calculate WCAG contrast ratio between foreground and background colors.
        
        Formula: (L1 + 0.05) / (L2 + 0.05) where L1 is lighter.
        """
        l1 = cls.calculate_relative_luminance(fg_rgb)
        l2 = cls.calculate_relative_luminance(bg_rgb)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        ratio = (lighter + 0.05) / (darker + 0.05)
        return round(ratio, 2)

    @classmethod
    def evaluate_contrast_rule(
        cls,
        fg_color: Union[str, Tuple[int, int, int]],
        bg_color: Union[str, Tuple[int, int, int]],
        element_selector: str,
        is_large_text: bool = False,
        bounding_box: Optional[BoundingBox] = None,
    ) -> Optional[EvidenceItem]:
        """Evaluate WCAG 2.1 AA and AAA color contrast requirements.
        
        WCAG AA:
            - Normal text: >= 4.5:1
            - Large text (>= 18pt or >= 14pt bold): >= 3.0:1
        WCAG AAA:
            - Normal text: >= 7.0:1
            - Large text: >= 4.5:1
        """
        fg_rgb = cls.parse_color_to_rgb(fg_color) if isinstance(fg_color, str) else fg_color
        bg_rgb = cls.parse_color_to_rgb(bg_color) if isinstance(bg_color, str) else bg_color

        if not fg_rgb or not bg_rgb:
            return None

        ratio = cls.calculate_contrast_ratio(fg_rgb, bg_rgb)
        min_aa = 3.0 if is_large_text else 4.5
        min_aaa = 4.5 if is_large_text else 7.0

        if ratio < min_aa:
            return EvidenceItem(
                element_selector=element_selector,
                bounding_box=bounding_box,
                rule_id="COLOR_CONTRAST_FAIL_AA",
                severity=Severity.CRITICAL,
                metric_value=f"{ratio}:1",
                recommended_min=f"{min_aa}:1",
                message=(
                    f"Color contrast ratio of {ratio}:1 fails WCAG AA minimum threshold of {min_aa}:1. "
                    "Inaccessible for users with low vision, cataract, or viewing under direct sunlight."
                ),
                category="vision",
            )
        elif ratio < min_aaa:
            return EvidenceItem(
                element_selector=element_selector,
                bounding_box=bounding_box,
                rule_id="COLOR_CONTRAST_FAIL_AAA",
                severity=Severity.WARNING,
                metric_value=f"{ratio}:1",
                recommended_min=f"{min_aaa}:1",
                message=(
                    f"Color contrast ratio of {ratio}:1 satisfies WCAG AA but fails WCAG AAA enhanced standard of {min_aaa}:1."
                ),
                category="vision",
            )
        return None

    @classmethod
    def analyze_screenshot_image(
        cls,
        image_input: Union[str, Image.Image],
    ) -> Dict[str, Any]:
        """Analyze visual density, whitespace ratio, and clutter index on a screenshot image.
        
        Args:
            image_input: File path string or PIL Image object.
            
        Returns:
            Dictionary with whitespace_ratio, visual_density, clutter_score, and EvidenceItems.
        """
        if isinstance(image_input, str):
            image = Image.open(image_input).convert("RGB")
        else:
            image = image_input.convert("RGB")

        w, h = image.size
        img_arr = np.array(image, dtype=np.float32)

        # Convert to Grayscale luminance array
        # Y = 0.299 R + 0.587 G + 0.114 B
        gray = 0.299 * img_arr[:, :, 0] + 0.587 * img_arr[:, :, 1] + 0.114 * img_arr[:, :, 2]

        # 1. Whitespace Ratio:
        # Measure proportion of pixels close to white/light background (> 240)
        # or uniform background color
        white_mask = (gray >= 238)
        # Also check if page has dark theme (dominant dark background < 25)
        dark_mask = (gray <= 25)
        dominant_background_pixels = max(np.sum(white_mask), np.sum(dark_mask))
        whitespace_ratio = round(float(dominant_background_pixels / (w * h)), 4)

        # 2. Visual Density:
        # Edge detection using discrete gradient differences along X and Y axes
        dx = np.abs(np.diff(gray, axis=1))
        dy = np.abs(np.diff(gray, axis=0))
        # Threshold for significant visual edges
        edge_threshold = 28.0
        edge_count = np.sum(dx > edge_threshold) + np.sum(dy > edge_threshold)
        total_possible_edges = (w - 1) * h + w * (h - 1)
        visual_density = round(float(edge_count / max(1, total_possible_edges)), 4)

        # 3. Clutter Score:
        # Divide image into 8x8 grid blocks and calculate spatial variance of edge density
        grid_rows, grid_cols = 8, 8
        tile_h = h // grid_rows
        tile_w = w // grid_cols

        densities = []
        if tile_h > 4 and tile_w > 4:
            for r in range(grid_rows):
                for c in range(grid_cols):
                    sub_gray = gray[r * tile_h : (r + 1) * tile_h, c * tile_w : (c + 1) * tile_w]
                    sub_dx = np.abs(np.diff(sub_gray, axis=1))
                    sub_dy = np.abs(np.diff(sub_gray, axis=0))
                    sub_edges = np.sum(sub_dx > edge_threshold) + np.sum(sub_dy > edge_threshold)
                    sub_total = (tile_w - 1) * tile_h + tile_w * (tile_h - 1)
                    densities.append(sub_edges / max(1, sub_total))

            # Clutter index is a combination of mean density and variance across screen
            mean_density = np.mean(densities)
            var_density = np.var(densities)
            # High clutter means dense edges packed unevenly
            clutter_score = round(float(min(1.0, (mean_density * 3.0) + (var_density * 20.0))), 3)
        else:
            clutter_score = round(float(min(1.0, visual_density * 4.0)), 3)

        evidence: List[EvidenceItem] = []

        if clutter_score > 0.65:
            evidence.append(
                EvidenceItem(
                    element_selector="body",
                    rule_id="HIGH_VISUAL_CLUTTER",
                    severity=Severity.WARNING,
                    metric_value=f"Clutter score: {clutter_score:.2f}, Whitespace: {whitespace_ratio * 100:.1f}%",
                    recommended_min="Clutter score <= 0.40, Whitespace >= 30%",
                    message=(
                        f"Page exhibits excessive visual clutter (score {clutter_score:.2f}). "
                        "High cognitive load and visual noise creates severe friction for neurodiverse and low-vision users."
                    ),
                    category="vision",
                )
            )

        if whitespace_ratio < 0.15:
            evidence.append(
                EvidenceItem(
                    element_selector="body",
                    rule_id="INSUFFICIENT_WHITESPACE",
                    severity=Severity.WARNING,
                    metric_value=f"Whitespace ratio: {whitespace_ratio * 100:.1f}%",
                    recommended_min="Whitespace >= 25%",
                    message=(
                        f"Page whitespace ratio is only {whitespace_ratio * 100:.1f}%. "
                        "Crammed visual presentation diminishes legibility and visual hierarchy."
                    ),
                    category="vision",
                )
            )

        return {
            "image_width": w,
            "image_height": h,
            "whitespace_ratio": whitespace_ratio,
            "visual_density": visual_density,
            "clutter_score": clutter_score,
            "evidence": evidence,
        }
