"""Text analyzer for readability, sentence complexity, and exclusionary/gendered terminology detection."""
from __future__ import annotations
import re
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup

from carbon.schemas.contracts import EvidenceItem, Severity


# Common exclusionary, gendered, or biased terms with inclusive alternatives
BIASED_TERMINOLOGY_DICTIONARY: Dict[str, Dict[str, str]] = {
    # Gendered professional/collective nouns
    "man hours": {"replacement": "person hours / labor hours", "category": "gender_bias"},
    "man-hours": {"replacement": "person-hours / labor-hours", "category": "gender_bias"},
    "mankind": {"replacement": "humankind / humanity", "category": "gender_bias"},
    "manpower": {"replacement": "workforce / personnel / staffing", "category": "gender_bias"},
    "chairman": {"replacement": "chair / chairperson", "category": "gender_bias"},
    "chairwoman": {"replacement": "chair / chairperson", "category": "gender_bias"},
    "policeman": {"replacement": "police officer", "category": "gender_bias"},
    "fireman": {"replacement": "firefighter", "category": "gender_bias"},
    "salesman": {"replacement": "sales representative / salesperson", "category": "gender_bias"},
    "spokesman": {"replacement": "spokesperson / representative", "category": "gender_bias"},
    "businessman": {"replacement": "business person / executive", "category": "gender_bias"},
    "mailman": {"replacement": "postal carrier / mail carrier", "category": "gender_bias"},
    "waitress": {"replacement": "server", "category": "gender_bias"},
    "stewardess": {"replacement": "flight attendant", "category": "gender_bias"},
    "housewife": {"replacement": "homemaker", "category": "gender_bias"},
    "you guys": {"replacement": "everyone / folks / team", "category": "gender_bias"},
    "freshman": {"replacement": "first-year student", "category": "gender_bias"},
    "master/slave": {"replacement": "primary/replica or controller/worker", "category": "exclusionary_jargon"},
    "whitelist": {"replacement": "allowlist", "category": "exclusionary_jargon"},
    "blacklist": {"replacement": "denylist / blocklist", "category": "exclusionary_jargon"},
    # Ableist idioms in UI/UX
    "blind to": {"replacement": "unaware of / inattentive to", "category": "ableism"},
    "fall on deaf ears": {"replacement": "be ignored / overlooked", "category": "ableism"},
    "crazy": {"replacement": "surprising / unexpected / erratic", "category": "ableism"},
    "insane": {"replacement": "extreme / unprecedented", "category": "ableism"},
    "crippled": {"replacement": "disabled / degraded / broken", "category": "ableism"},
}

COMMON_ABBREVIATIONS = [
    "e.g.", "i.e.", "etc.", "vs.", "dr.", "mr.", "mrs.", "ms.",
    "prof.", "inc.", "ltd.", "no.", "fig.", "dept.", "approx.", "est."
]


class TextAnalyzer:
    """Multi-modal text analyzer analyzing reading ease, complexity, and inclusive language."""

    def __init__(self, biased_terms: Optional[Dict[str, Dict[str, str]]] = None):
        self.biased_terms = biased_terms or BIASED_TERMINOLOGY_DICTIONARY

    @staticmethod
    def extract_clean_text_from_html(html_content: str) -> str:
        """Extract user-visible text from an HTML document, stripping code, styles, and scripts."""
        if not html_content or not html_content.strip():
            return ""

        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "head", "meta", "link"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def split_sentences_robustly(text: str) -> List[str]:
        """Split text into sentences without false splits on abbreviations, decimals, or currency."""
        if not text or not text.strip():
            return []

        cleaned = text
        # Protect abbreviations (e.g. "e.g.", "Dr.", "vs.") while preserving exact casing
        def _mask_abbrev(m: re.Match) -> str:
            return m.group(0).replace(".", "@DOT@")

        for ab in COMMON_ABBREVIATIONS:
            cleaned = re.sub(re.escape(ab), _mask_abbrev, cleaned, flags=re.IGNORECASE)

        # Protect decimals and currency (e.g. 3.5, $19.99)
        cleaned = re.sub(r"(\d+)\.(\d+)", r"\1@DOT@\2", cleaned)

        # Split on sentence boundaries: [.!?] followed by whitespace
        raw_splits = re.split(r"[.!?]+\s+", cleaned)
        sentences = []
        for s in raw_splits:
            restored = s.replace("@DOT@", ".").strip()
            if len(restored) > 1:
                sentences.append(restored)

        return sentences or [text.strip()]

    @staticmethod
    def count_syllables_in_word(word: str) -> int:
        """Estimate syllable count in an English word using phonetic heuristic rules."""
        word = word.lower().strip()
        if not word:
            return 0
        word = re.sub(r"[^a-z]", "", word)
        if len(word) <= 3:
            return 1

        # Remove silent 'e' at end unless word ends in 'le' preceded by consonant
        if word.endswith("e") and not word.endswith("le"):
            word = word[:-1]

        # Group vowel sequences (ai, ea, ou, etc. typically count as 1 syllable)
        vowel_runs = re.findall(r"[aeiouy]+", word)
        count = len(vowel_runs)

        # Handle endings like -ed, -es that don't add syllables unless preceded by t/d
        if word.endswith("ed") and len(word) > 4:
            if word[-3] not in ("t", "d"):
                count = max(1, count - 1)

        return max(1, count)

    def analyze_text(self, text: str, source_selector: str = "body") -> Dict[str, Any]:
        """Perform comprehensive text analysis on raw text."""
        if not text or not text.strip():
            return {
                "word_count": 0,
                "sentence_count": 0,
                "syllable_count": 0,
                "flesch_reading_ease": 100.0,
                "flesch_kincaid_grade": 0.0,
                "avg_words_per_sentence": 0.0,
                "avg_syllables_per_word": 0.0,
                "complex_sentences_count": 0,
                "flagged_terms": [],
                "evidence": [],
            }

        # Tokenize sentences robustly
        sentences = self.split_sentences_robustly(text)
        sentence_count = max(1, len(sentences))

        # Tokenize words
        words = re.findall(r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b", text)
        word_count = max(1, len(words))

        # Count syllables
        total_syllables = sum(self.count_syllables_in_word(w) for w in words)

        # Averages
        avg_words_per_sentence = word_count / sentence_count
        avg_syllables_per_word = total_syllables / word_count

        # Flesch Reading Ease: 206.835 - (1.015 * ASL) - (84.6 * ASW)
        reading_ease = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
        reading_ease = max(0.0, min(100.0, round(reading_ease, 2)))

        # Flesch-Kincaid Grade Level: 0.39 * ASL + 11.8 * ASW - 15.59
        grade_level = (0.39 * avg_words_per_sentence) + (11.8 * avg_syllables_per_word) - 15.59
        grade_level = max(0.0, round(grade_level, 2))

        # Complex sentences (e.g. > 25 words)
        complex_sentences = [s for s in sentences if len(re.findall(r"\b\w+\b", s)) > 25]

        # Scan for exclusionary / gendered / biased terminology
        flagged_terms = self.find_biased_terminology(text)

        evidence: List[EvidenceItem] = []

        # Readability rule evaluations
        if grade_level > 12.0:
            evidence.append(
                EvidenceItem(
                    element_selector=source_selector,
                    rule_id="HIGH_READING_DIFFICULTY",
                    severity=Severity.CRITICAL if grade_level > 16.0 else Severity.WARNING,
                    metric_value=f"Grade {grade_level} (Flesch Ease: {reading_ease})",
                    recommended_min="Grade <= 8.0 (Plain Language Standard)",
                    message=(
                        f"Content requires college-level reading comprehension (Grade {grade_level}). "
                        "Creates high cognitive barrier for users with cognitive or learning disabilities."
                    ),
                    category="text",
                )
            )

        # Flagged terms evidence (for plain text inputs where HTML elements are not available)
        for flag in flagged_terms:
            evidence.append(
                EvidenceItem(
                    element_selector=source_selector,
                    rule_id="EXCLUSIONARY_LANGUAGE_DETECTED",
                    severity=Severity.WARNING,
                    metric_value=f"Found: '{flag['term']}'",
                    recommended_min=f"Use: '{flag['replacement']}'",
                    message=(
                        f"Non-inclusive term '{flag['term']}' detected in {source_selector}. "
                        f"Recommended inclusive replacement: {flag['replacement']}."
                    ),
                    category="text",
                )
            )

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "syllable_count": total_syllables,
            "flesch_reading_ease": reading_ease,
            "flesch_kincaid_grade": grade_level,
            "avg_words_per_sentence": round(avg_words_per_sentence, 2),
            "avg_syllables_per_word": round(avg_syllables_per_word, 2),
            "complex_sentences_count": len(complex_sentences),
            "complex_sentences": complex_sentences[:5],
            "flagged_terms": flagged_terms,
            "evidence": evidence,
        }

    def find_biased_terminology(self, text: str) -> List[Dict[str, str]]:
        """Find occurrences of biased or exclusionary terms in the text."""
        findings = []
        lower_text = text.lower()

        for term, info in self.biased_terms.items():
            pattern = rf"\b{re.escape(term)}\b"
            for match in re.finditer(pattern, lower_text):
                findings.append({
                    "term": term,
                    "replacement": info["replacement"],
                    "category": info["category"],
                    "start": match.start(),
                    "end": match.end(),
                })
        return findings

    def analyze_html_elements(self, html_content: str) -> List[EvidenceItem]:
        """Analyze individual content elements in HTML without ancestor double-counting."""
        if not html_content or not html_content.strip():
            return []

        evidence: List[EvidenceItem] = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip non-visual tags
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        seen_findings = set()

        # Target candidate tags from specific to broad
        target_tags = soup.find_all(
            ["span", "button", "a", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "section"]
        )

        for idx, tag in enumerate(target_tags):
            tag_name = tag.name
            text = tag.get_text(strip=True)
            if not text or len(text) < 3:
                continue

            lower_text = text.lower()
            for term, info in self.biased_terms.items():
                pattern = rf"\b{re.escape(term)}\b"
                if re.search(pattern, lower_text):
                    # Check if any child tag inside this tag also contains the term
                    child_has_term = False
                    for child in tag.find_all(True):
                        child_text = child.get_text(strip=True).lower()
                        if re.search(pattern, child_text):
                            child_has_term = True
                            break

                    # Defer to child tag to prevent ancestor duplication
                    if child_has_term:
                        continue

                    elem_id = tag.get("id")
                    selector = f"{tag_name}#{elem_id}" if elem_id else f"{tag_name}:nth-of-type({idx+1})"

                    dedup_key = (selector, term)
                    if dedup_key not in seen_findings:
                        seen_findings.add(dedup_key)
                        evidence.append(
                            EvidenceItem(
                                element_selector=selector,
                                rule_id="EXCLUSIONARY_LANGUAGE_DETECTED",
                                severity=Severity.WARNING,
                                metric_value=f"Found: '{term}'",
                                recommended_min=f"Use: '{info['replacement']}'",
                                message=f"Exclusive term '{term}' found in {selector}. Suggestion: '{info['replacement']}'",
                                category="text",
                            )
                        )

        return evidence
