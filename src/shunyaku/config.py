from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    model_repo: str = os.getenv(
        "SHUNYAKU_MODEL_REPO",
        "LiquidAI/LFM2-350M-ENJP-MT-GGUF",
    )
    model_quant: str = os.getenv(
        "SHUNYAKU_MODEL_QUANT",
        "Q8_0",
    )
    double_copy_window_ms: int = int(
        os.getenv("SHUNYAKU_DOUBLE_COPY_WINDOW_MS", "750")
    )
    max_tokens: int = int(os.getenv("SHUNYAKU_MAX_TOKENS", "256"))
    context_length: int = int(os.getenv("SHUNYAKU_CTX", "2048"))
    gpu_layers: int = int(os.getenv("SHUNYAKU_GPU_LAYERS", "0"))
    temperature: float = float(os.getenv("SHUNYAKU_TEMPERATURE", "0.5"))
    top_p: float = float(os.getenv("SHUNYAKU_TOP_P", "1.0"))
    min_p: float = float(os.getenv("SHUNYAKU_MIN_P", "0.1"))
    repetition_penalty: float = float(
        os.getenv("SHUNYAKU_REPETITION_PENALTY", "1.05")
    )
