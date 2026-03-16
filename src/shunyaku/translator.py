from __future__ import annotations

import re
from concurrent.futures import Future, ThreadPoolExecutor

from llama_cpp import Llama

from .config import AppConfig

PROMPT_TEMPLATE = """<|im_start|>system
Translate to Japanese.<|im_end|>
<|im_start|>user
{text}<|im_end|>
<|im_start|>assistant
"""


class TranslationError(RuntimeError):
    pass


class Translator:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="translate")
        self._model: Llama | None = None

    def warmup_async(self) -> Future[None]:
        return self._executor.submit(self._ensure_model)

    def translate_async(self, text: str) -> Future[str]:
        return self._executor.submit(self.translate, text)

    def translate(self, text: str) -> str:
        normalized = text.strip()
        if not normalized:
            raise TranslationError("クリップボードが空です。")

        if not self.looks_like_english(normalized):
            raise TranslationError("英語テキストが見つかりませんでした。")

        model = self._ensure_model()
        prompt = PROMPT_TEMPLATE.format(text=normalized)
        result = model(
            prompt,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
            top_p=self._config.top_p,
            min_p=self._config.min_p,
            repeat_penalty=self._config.repetition_penalty,
            stop=["<|im_end|>"],
            echo=False,
        )
        translated = result["choices"][0]["text"].strip()
        if not translated:
            raise TranslationError("翻訳結果を生成できませんでした。")
        return translated

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _ensure_model(self) -> Llama:
        if self._model is not None:
            return self._model

        filename_glob = f"*{self._config.model_quant}*.gguf"
        self._model = Llama.from_pretrained(
            repo_id=self._config.model_repo,
            filename=filename_glob,
            n_ctx=self._config.context_length,
            n_gpu_layers=self._config.gpu_layers,
            verbose=False,
        )
        return self._model

    @staticmethod
    def looks_like_english(text: str) -> bool:
        ascii_letters = re.findall(r"[A-Za-z]", text)
        visible_chars = re.findall(r"[A-Za-z0-9]", text)
        if len(ascii_letters) < 3:
            return False
        if not visible_chars:
            return False
        return (len(ascii_letters) / len(visible_chars)) >= 0.45
