from __future__ import annotations

import re
from concurrent.futures import Future

from llama_cpp import Llama

from .background import DaemonThreadPoolExecutor
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
        self._executor = DaemonThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="translate",
        )
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
        chunks = self._split_text_to_fit(model, normalized)
        translated_chunks = [self._translate_chunk(model, chunk) for chunk in chunks]
        return "\n\n".join(chunk for chunk in translated_chunks if chunk)

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

    def _translate_chunk(self, model: Llama, text: str) -> str:
        prompt = PROMPT_TEMPLATE.format(text=text)
        max_tokens = self._available_completion_tokens(model, text)
        if max_tokens < 16:
            raise TranslationError(
                "入力テキストが長すぎて、翻訳結果の生成余地がありません。もっと短い単位でコピーしてください。"
            )
        # 独立した翻訳ごとに前回の prefix-match 最適化を無効化して、
        # KV キャッシュ状態の持ち越しによる不安定化を避ける。
        model.reset()
        try:
            result = model(
                prompt,
                max_tokens=max_tokens,
                temperature=self._config.temperature,
                top_p=self._config.top_p,
                min_p=self._config.min_p,
                repeat_penalty=self._config.repetition_penalty,
                stop=["<|im_end|>"],
                echo=False,
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip()
            if message:
                raise TranslationError(
                    f"モデル推論に失敗しました。\n{message}"
                ) from exc
            raise TranslationError(
                "モデル推論に失敗しました。入力が長すぎるか、モデル初期化に失敗した可能性があります。"
            ) from exc

        translated = result["choices"][0]["text"].strip()
        if not translated:
            raise TranslationError("翻訳結果を生成できませんでした。")
        return translated

    def _split_text_to_fit(self, model: Llama, text: str) -> list[str]:
        if self._fits_context(model, text):
            return [text]

        chunks: list[str] = []
        for paragraph in self._split_preserving_order(text, r"\n\s*\n"):
            self._append_fitting_chunks(model, chunks, paragraph, r"(?<=[.!?])\s+")
        return chunks

    def _append_fitting_chunks(
        self,
        model: Llama,
        chunks: list[str],
        text: str,
        separator_pattern: str,
    ) -> None:
        normalized = text.strip()
        if not normalized:
            return
        if self._fits_context(model, normalized):
            chunks.append(normalized)
            return

        units = self._split_preserving_order(normalized, separator_pattern)
        if len(units) == 1:
            self._append_word_chunks(model, chunks, normalized)
            return

        current = ""
        for unit in units:
            candidate = unit if not current else f"{current} {unit}"
            if self._fits_context(model, candidate):
                current = candidate
                continue
            if current:
                chunks.append(current)
            if self._fits_context(model, unit):
                current = unit
                continue
            self._append_word_chunks(model, chunks, unit)
            current = ""

        if current:
            chunks.append(current)

    def _append_word_chunks(self, model: Llama, chunks: list[str], text: str) -> None:
        words = text.split()
        if not words:
            return

        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if self._fits_context(model, candidate):
                current = candidate
                continue
            if current:
                chunks.append(current)
                current = word
                continue
            raise TranslationError(
                "入力テキストが長すぎます。もっと短い単位でコピーしてください。"
            )

        if current:
            chunks.append(current)

    def _fits_context(self, model: Llama, text: str) -> bool:
        return self._available_completion_tokens(model, text) >= min(
            self._config.max_tokens,
            64,
        )

    def _available_completion_tokens(self, model: Llama, text: str) -> int:
        prompt = PROMPT_TEMPLATE.format(text=text)
        prompt_tokens = len(model.tokenize(prompt.encode("utf-8")))
        reserve_tokens = 128
        available = self._config.context_length - prompt_tokens - reserve_tokens
        return max(0, min(self._config.max_tokens, available))

    @staticmethod
    def _split_preserving_order(text: str, pattern: str) -> list[str]:
        return [segment.strip() for segment in re.split(pattern, text) if segment.strip()]

    @staticmethod
    def looks_like_english(text: str) -> bool:
        ascii_letters = re.findall(r"[A-Za-z]", text)
        visible_chars = re.findall(r"[A-Za-z0-9]", text)
        if len(ascii_letters) < 3:
            return False
        if not visible_chars:
            return False
        return (len(ascii_letters) / len(visible_chars)) >= 0.45
