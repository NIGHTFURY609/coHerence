"""Helium on one shared B300. From repo root: modal run helium/modal_app.py

Same run: Hydrogen scores on the local CPU process, Helium completes on GPU.
Same replica: other team models load here (Helium KV is 8 GiB). Do not add
another @app.cls(gpu="B300"). GPU methods must not import hydrogen.

Keep REPORT_MODEL / GPU settings in sync with helium/constants.py.
"""

from __future__ import annotations

import json

import modal

GPU = "B300"
MAX_MODEL_LEN = 8192
KV_CACHE_GIB = 8
KV_CACHE_MEMORY_BYTES = KV_CACHE_GIB * 1024**3
MAX_NUM_SEQS = 8
GPU_MEMORY_UTILIZATION = 0.26
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
        self.helium = _make_llm()

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
        try:
            result = self.helium.generate([prompt], params, use_tqdm=False)[0]
        except TypeError:
            result = self.helium.generate([prompt], params)[0]
        output = result.outputs[0]
        if getattr(output, "finish_reason", None) == "length":
            raise ValueError("Helium output truncated (max_tokens); raise max_tokens")
        return _require_both_fields(_json_only(output.text))


def _make_llm():
    from vllm import LLM

    base = {
        "model": REPORT_MODEL,
        "max_model_len": MAX_MODEL_LEN,
        "max_num_seqs": MAX_NUM_SEQS,
        "dtype": "auto",
    }
    for key in ("kv_cache_memory_bytes", "kv_cache_memory"):
        try:
            return LLM(**base, **{key: KV_CACHE_MEMORY_BYTES})
        except TypeError:
            continue
    return LLM(**base, gpu_memory_utilization=GPU_MEMORY_UTILIZATION)


def _sampling_params():
    from vllm import SamplingParams

    kwargs = {"max_tokens": 1024, "temperature": 0.0}
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


def _finished_sentence(text: str) -> bool:
    t = text.strip()
    return bool(t) and t[-1] in ".!?"


def _require_both_fields(raw: str) -> str:
    payload = json.loads(raw)
    diagnosis = str(payload.get("diagnosis") or "").strip()
    remediation = str(payload.get("remediation") or "").strip()
    if not diagnosis or not remediation:
        raise ValueError("Helium JSON must include non-empty diagnosis and remediation")
    if not _finished_sentence(diagnosis) or not _finished_sentence(remediation):
        raise ValueError("Helium diagnosis and remediation must be complete sentences")
    return json.dumps(
        {"diagnosis": diagnosis, "remediation": remediation},
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
        f"(kv_cache={KV_CACHE_GIB} GiB)"
    )
    scored = evaluate(example_bundle(), "rep_example")
    out = diagnose(scored, ModalLLMClient())
    print()
    print(
        json.dumps(
            {
                "overall_fairness_score": out.overall_fairness_score,
                "analyst": out.analyst,
                "diagnosis": out.diagnosis,
                "remediation": out.remediation,
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )
