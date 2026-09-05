"""Helium on one shared B300. From repo root: modal run helium/modal_app.py

Same run: Hydrogen scores on the local CPU process, Helium completes on GPU.
Same replica: other team models load here (leave 0.42 util). Do not add
another @app.cls(gpu="B300"). GPU methods must not import hydrogen.

Keep REPORT_MODEL / GPU settings in sync with helium/constants.py.
"""

from __future__ import annotations

import json

import modal

GPU = "B300"
MAX_MODEL_LEN = 8192
GPU_MEMORY_UTILIZATION = 0.42
REPORT_MODEL = "Qwen/Qwen3.6-27B"
MODAL_APP_NAME = "coherence-helium"

HELIUM_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "diagnosis": {"type": "string"},
        "remediation": {"type": "string"},
    },
    "required": ["diagnosis", "remediation"],
    "additionalProperties": False,
}

app = modal.App(MODAL_APP_NAME)

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
    """Shared B300 replica. Helium owns `helium` + `complete`. Other models load here."""

    @modal.enter()
    def load(self) -> None:
        from vllm import LLM

        self.helium = LLM(
            model=REPORT_MODEL,
            max_model_len=MAX_MODEL_LEN,
            gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
            dtype="auto",
        )

    @modal.method()
    def complete(self, system: str, user: str) -> str:
        from vllm import SamplingParams

        tokenizer = self.helium.get_tokenizer()
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
        params = _sampling_params()
        raw = self.helium.generate([prompt], params)[0].outputs[0].text
        return _require_both_fields(_json_only(raw))


def _sampling_params():
    from vllm import SamplingParams

    kwargs = {"max_tokens": 400, "temperature": 0.0}
    try:
        from vllm.sampling_params import StructuredOutputsParams

        kwargs["structured_outputs"] = StructuredOutputsParams(json=HELIUM_JSON_SCHEMA)
        return SamplingParams(**kwargs)
    except Exception:
        pass
    try:
        return SamplingParams(**kwargs, extra_args={"guided_json": HELIUM_JSON_SCHEMA})
    except TypeError:
        return SamplingParams(**kwargs)


def _json_only(raw: str) -> str:
    text = raw.strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[-1].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _require_both_fields(raw: str) -> str:
    payload = json.loads(raw)
    if not payload.get("diagnosis") or not payload.get("remediation"):
        raise ValueError("Helium JSON must include non-empty diagnosis and remediation")
    return json.dumps(
        {
            "diagnosis": str(payload["diagnosis"]).strip(),
            "remediation": str(payload["remediation"]).strip(),
        },
        ensure_ascii=False,
    )


@app.local_entrypoint()
def main() -> None:
    from helium.client import ModalLLMClient
    from helium.engine import diagnose
    from helium.example import example_bundle
    from hydrogen.engine import evaluate

    print(
        f"Starting Helium on {GPU} with {REPORT_MODEL} "
        f"(gpu_memory_utilization={GPU_MEMORY_UTILIZATION})"
    )
    scored = evaluate(example_bundle(), "rep_example")
    out = diagnose(scored, ModalLLMClient())
    print(
        json.dumps(
            {
                "overall_fairness_score": out.overall_fairness_score,
                "analyst": out.analyst,
                "diagnosis": out.diagnosis,
                "remediation": out.remediation,
            },
            ensure_ascii=False,
        )
    )
