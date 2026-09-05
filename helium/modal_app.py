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
NITROGEN_GPU_MEMORY_UTILIZATION = 0.65
REPORT_MODEL = "Qwen/Qwen3.6-27B"
NITROGEN_MODEL = "Qwen/Qwen3-VL-30B-A3B-Instruct"
NITROGEN_KV_CACHE_MEMORY_BYTES = 8 * 1024**3
OXYGEN_MODEL = "Qwen/Qwen3.5-9B"
OXYGEN_KV_CACHE_MEMORY_BYTES = 4 * 1024**3
OXYGEN_GPU_MEMORY_UTILIZATION = 0.35
FLUORINE_MODEL = "google/gemma-4-26B-A4B-it"
FLUORINE_KV_CACHE_MEMORY_BYTES = 8 * 1024**3
FLUORINE_GPU_MEMORY_UTILIZATION = 0.32
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
    .pip_install("vllm", "huggingface_hub", "pillow")
)


@app.cls(
    gpu=GPU,
    image=image,
    timeout=60 * 60,
    startup_timeout=60 * 60,
    scaledown_window=60 * 60,
    min_containers=1,
    max_containers=1,
    volumes={"/root/.cache/huggingface": hf_cache},
)
class HeliumGPU:
    """One B300. Helium + Nitrogen + Oxygen + Fluorine; generates take turns."""

    @modal.enter()
    def load(self) -> None:
        import threading

        self._turn = threading.Lock()
        self.helium = _make_llm()
        self.nitrogen = _make_nitrogen_llm()
        self.oxygen = _make_oxygen_llm()
        self.fluorine = _make_fluorine_llm()

    def _ensure_nitrogen(self):
        if getattr(self, "nitrogen", None) is None:
            self.nitrogen = _make_nitrogen_llm()
        return self.nitrogen

    @modal.method()
    def load_nitrogen(self) -> str:
        """Download Qwen3-VL-30B onto the shared HF volume and load it."""
        self._ensure_nitrogen()
        return NITROGEN_MODEL

    @modal.method()
    def load_all(self) -> dict:
        """All three engines already loaded in enter(); returns their ids."""
        return {
            "helium": REPORT_MODEL,
            "nitrogen": NITROGEN_MODEL,
            "oxygen": OXYGEN_MODEL,
            "fluorine": FLUORINE_MODEL,
        }

    @modal.method()
    def fluorine_complete(
        self, system: str, user: str, image_b64: str | None = None
    ) -> str:
        from vllm import SamplingParams

        tokenizer = self.fluorine.get_tokenizer()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if image_b64:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                        {"type": "text", "text": user},
                    ],
                }
            )
        else:
            messages.append({"role": "user", "content": user})
        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except TypeError:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        params = SamplingParams(max_tokens=1024, temperature=0.0)
        with self._turn:
            try:
                result = self.fluorine.generate([prompt], params, use_tqdm=False)[0]
            except TypeError:
                result = self.fluorine.generate([prompt], params)[0]
        return result.outputs[0].text

    @modal.method()
    def oxygen_complete(self, system: str, user: str) -> str:
        from vllm import SamplingParams

        tokenizer = self.oxygen.get_tokenizer()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
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
        params = SamplingParams(max_tokens=1024, temperature=0.0)
        with self._turn:
            try:
                result = self.oxygen.generate([prompt], params, use_tqdm=False)[0]
            except TypeError:
                result = self.oxygen.generate([prompt], params)[0]
        return result.outputs[0].text

    @modal.method()
    def nitrogen_complete(
        self, system: str, user: str, image_b64: str | None = None
    ) -> str:
        llm = self._ensure_nitrogen()
        from vllm import SamplingParams

        tokenizer = llm.get_tokenizer()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if image_b64:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        {"type": "text", "text": user},
                    ],
                }
            )
        else:
            messages.append({"role": "user", "content": user})
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
        params = SamplingParams(max_tokens=1024, temperature=0.0)
        with self._turn:
            try:
                result = llm.generate([prompt], params, use_tqdm=False)[0]
            except TypeError:
                result = llm.generate([prompt], params)[0]
        return result.outputs[0].text

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
        with self._turn:
            try:
                result = self.helium.generate([prompt], params, use_tqdm=False)[0]
            except TypeError:
                result = self.helium.generate([prompt], params)[0]
        output = result.outputs[0]
        if getattr(output, "finish_reason", None) == "length":
            raise ValueError("Helium output truncated (max_tokens); raise max_tokens")
        return _require_both_fields(_json_only(output.text))


def _share_gpu_utilization(ceiling: float) -> float:
    """vLLM requires free >= util * total card, not remaining. Cap to what's free."""
    try:
        import torch

        free, total = torch.cuda.mem_get_info()
        if total:
            return min(ceiling, max(0.10, (free / total) * 0.85))
    except Exception:
        pass
    return ceiling


def _make_engine(model: str, kv_bytes: int, util: float, multimodal: bool = False):
    from vllm import LLM

    base = {
        "model": model,
        "max_model_len": MAX_MODEL_LEN,
        "max_num_seqs": MAX_NUM_SEQS,
        "dtype": "auto",
        "gpu_memory_utilization": _share_gpu_utilization(util),
    }
    if multimodal:
        base["limit_mm_per_prompt"] = {"image": 1}
    for key in ("kv_cache_memory_bytes", "kv_cache_memory"):
        try:
            return LLM(**base, **{key: kv_bytes})
        except TypeError:
            continue
    if multimodal:
        base.pop("limit_mm_per_prompt", None)
        try:
            return LLM(**base, kv_cache_memory_bytes=kv_bytes)
        except TypeError:
            pass
    return LLM(**base)


def _make_llm():
    return _make_engine(REPORT_MODEL, KV_CACHE_MEMORY_BYTES, GPU_MEMORY_UTILIZATION)


def _make_nitrogen_llm():
    return _make_engine(
        NITROGEN_MODEL,
        NITROGEN_KV_CACHE_MEMORY_BYTES,
        NITROGEN_GPU_MEMORY_UTILIZATION,
        multimodal=True,
    )


def _make_oxygen_llm():
    return _make_engine(
        OXYGEN_MODEL,
        OXYGEN_KV_CACHE_MEMORY_BYTES,
        OXYGEN_GPU_MEMORY_UTILIZATION,
    )


def _make_fluorine_llm():
    return _make_engine(
        FLUORINE_MODEL,
        FLUORINE_KV_CACHE_MEMORY_BYTES,
        FLUORINE_GPU_MEMORY_UTILIZATION,
        multimodal=True,
    )


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


@app.local_entrypoint()
def pull_nitrogen() -> None:
    print(f"Pulling {NITROGEN_MODEL} onto the shared B300 (helium-hf-cache)")
    name = HeliumGPU().load_nitrogen.remote()
    print(f"ready: {name}")


@app.local_entrypoint()
def warm_all() -> None:
    print(
        "Loading Helium + Nitrogen + Oxygen + Fluorine on one B300 "
        f"(max_num_seqs={MAX_NUM_SEQS})"
    )
    names = HeliumGPU().load_all.remote()
    print(json.dumps(names, indent=2), flush=True)
