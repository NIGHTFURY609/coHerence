"""Helium on one B300. From repo root: modal run helium/modal_app.py

This file is self-contained: the remote container does not import the helium package.
Keep REPORT_MODEL in sync with helium/constants.py.
"""

from __future__ import annotations

import modal

# Duplicated on purpose so /root/modal_app.py has no helium.* imports.
GPU = "B300"
MAX_MODEL_LEN = 16384
REPORT_MODEL = "Qwen/Qwen3.6-27B"

SYSTEM_PROMPT = """You write one diagnosis and one remediation for an inclusive-design test report.

Rules:
- Use only the JSON evidence you are given. Do not invent WCAG, users, or metrics.
- Consider all evidence streams that are present. Prioritize what is relevant to the strongest findings and the observed disparity. Do not mention every row.
- Write about constraints and interface evidence, never personas or stereotypes.
- If attribution is UNRESOLVED, state facts side by side. Do not say one caused the other.
- Do not change or invent the fairness score. You may quote a gap that is in the input.
- Short paragraphs. No chain-of-thought. No preamble.

Reply with JSON only, matching:
{"diagnosis": "...", "remediation": "..."}
Do not output <think> or analysis. JSON object only.
"""

SMOKE_USER = """Synthesize one diagnosis and one remediation. Reply with JSON only:
{"diagnosis": "...", "remediation": "..."}

Hydrogen:
  completion gap = 28 pp

Text Analyzer:
  instruction is ambiguous

Vision Analyzer:
  primary action has low visual prominence

A11Y:
  keyboard navigation requires 14 steps

Interaction:
  constrained profile made 3 additional errors
"""

app = modal.App("coherence-helium")

hf_cache = modal.Volume.from_name("helium-hf-cache", create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:13.1.0-devel-ubuntu22.04",
        add_python="3.12",
    )
    .entrypoint([])
    .pip_install("vllm", "huggingface_hub")
)


@app.cls(
    gpu=GPU,
    image=image,
    timeout=60 * 60,
    scaledown_window=10 * 60,
    volumes={"/root/.cache/huggingface": hf_cache},
)
class HeliumGPU:
    @modal.enter()
    def load(self) -> None:
        from vllm import LLM

        self.llm = LLM(
            model=REPORT_MODEL,
            max_model_len=MAX_MODEL_LEN,
            dtype="auto",
        )

    @modal.method()
    def complete(self, system: str, user: str) -> str:
        from vllm import SamplingParams

        tokenizer = self.llm.get_tokenizer()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        params = SamplingParams(max_tokens=512, temperature=0.1)
        raw = self.llm.generate([prompt], params)[0].outputs[0].text
        return _json_only(raw)


def _json_only(raw: str) -> str:
    text = raw.strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[-1].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


@app.local_entrypoint()
def main() -> None:
    print(f"Starting Helium on {GPU} with {REPORT_MODEL} (cached weights on GPU if volume hit)")
    text = HeliumGPU().complete.remote(SYSTEM_PROMPT, SMOKE_USER)
    print(text)
