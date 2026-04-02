from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path

from .background import DaemonThreadPoolExecutor

SCREEN_CAPTURE_COMMAND = "/usr/sbin/screencapture"
LINE_MERGE_TOLERANCE = 0.03


class OCRError(RuntimeError):
    pass


class OCRUnavailableError(OCRError):
    pass


class OCRPermissionError(OCRError):
    pass


class OCRCaptureError(OCRError):
    pass


class OCRNoTextError(OCRError):
    pass


@dataclass(frozen=True)
class OCRTextObservation:
    text: str
    min_x: float
    min_y: float
    width: float
    height: float

    @property
    def center_y(self) -> float:
        return self.min_y + (self.height / 2)


@dataclass
class _OCRLine:
    observations: list[OCRTextObservation]
    center_y: float
    max_height: float

    @classmethod
    def from_observation(cls, observation: OCRTextObservation) -> _OCRLine:
        return cls(
            observations=[observation],
            center_y=observation.center_y,
            max_height=observation.height,
        )

    def can_merge(self, observation: OCRTextObservation) -> bool:
        tolerance = max(
            LINE_MERGE_TOLERANCE,
            max(self.max_height, observation.height) * 0.6,
        )
        return abs(self.center_y - observation.center_y) <= tolerance

    def add(self, observation: OCRTextObservation) -> None:
        self.observations.append(observation)
        count = len(self.observations)
        self.center_y = ((self.center_y * (count - 1)) + observation.center_y) / count
        self.max_height = max(self.max_height, observation.height)


class ScreenOCR:
    def __init__(self) -> None:
        self._executor = DaemonThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="screen_ocr",
        )

    def capture_text_async(self) -> Future[str | None]:
        return self._executor.submit(self.capture_text)

    def capture_text(self) -> str | None:
        capture_path = self._create_capture_path()
        try:
            if not self._capture_image(capture_path):
                return None
            return self._extract_text_from_capture(capture_path)
        finally:
            capture_path.unlink(missing_ok=True)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _create_capture_path(self) -> Path:
        fd, raw_path = tempfile.mkstemp(prefix="shunyaku-ocr-", suffix=".png")
        os.close(fd)
        return Path(raw_path)

    def _capture_image(self, capture_path: Path) -> bool:
        completed = self._run_screencapture(capture_path)
        stderr = (completed.stderr or "").strip()

        if completed.returncode == 0:
            if capture_path.exists() and capture_path.stat().st_size > 0:
                return True
            raise OCRCaptureError("スクリーンショットを取得できませんでした。")

        if self._looks_like_cancel(stderr, capture_path):
            return False

        if self._looks_like_permission_error(stderr):
            raise OCRPermissionError(
                "Screen Recording 権限がありません。\n"
                "システム設定 > プライバシーとセキュリティ > 画面収録 を確認してください。"
            )

        detail = stderr or "選択範囲のキャプチャに失敗しました。"
        raise OCRCaptureError(detail)

    def _run_screencapture(self, capture_path: Path) -> subprocess.CompletedProcess[str]:
        if sys.platform != "darwin":
            raise OCRUnavailableError("OCR 範囲翻訳は macOS 専用です。")

        try:
            return subprocess.run(
                [
                    SCREEN_CAPTURE_COMMAND,
                    "-i",
                    "-s",
                    "-x",
                    str(capture_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise OCRUnavailableError("macOS のスクリーンキャプチャ機能が見つかりません。") from exc

    def _extract_text_from_capture(self, capture_path: Path) -> str:
        observations = self._recognize_text(capture_path)
        text = self._combine_observations(observations)
        if not text:
            raise OCRNoTextError("文字を検出できませんでした。")
        return text

    def _recognize_text(self, capture_path: Path) -> list[OCRTextObservation]:
        Quartz, Vision = self._load_vision_frameworks()
        cg_image = self._load_cg_image(Quartz, capture_path)

        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setRecognitionLanguages_(["en-US"])
        request.setUsesLanguageCorrection_(True)

        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
            cg_image,
            None,
        )
        succeeded, error = handler.performRequests_error_([request], None)
        if not succeeded:
            detail = str(error).strip() if error is not None else "Vision OCR に失敗しました。"
            raise OCRCaptureError(detail)

        observations: list[OCRTextObservation] = []
        for observation in request.results() or []:
            candidates = observation.topCandidates_(1)
            if not candidates:
                continue
            text = str(candidates[0].string()).strip()
            if not text:
                continue
            bbox = observation.boundingBox()
            observations.append(
                OCRTextObservation(
                    text=text,
                    min_x=float(bbox.origin.x),
                    min_y=float(bbox.origin.y),
                    width=float(bbox.size.width),
                    height=float(bbox.size.height),
                )
            )
        return observations

    def _load_vision_frameworks(self):
        try:
            import Quartz
            import Vision
        except ImportError as exc:
            raise OCRUnavailableError(
                "OCR 機能の依存関係が見つかりません。\n"
                "pyobjc-framework-Vision と pyobjc-framework-Quartz をインストールしてください。"
            ) from exc
        return Quartz, Vision

    def _load_cg_image(self, Quartz, capture_path: Path):
        path_bytes = str(capture_path).encode("utf-8")
        url = Quartz.CFURLCreateFromFileSystemRepresentation(
            None,
            path_bytes,
            len(path_bytes),
            False,
        )
        if url is None:
            raise OCRCaptureError("OCR 用画像の URL を作成できませんでした。")

        source = Quartz.CGImageSourceCreateWithURL(url, None)
        if source is None:
            raise OCRCaptureError("OCR 用画像を読み込めませんでした。")

        cg_image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
        if cg_image is None:
            raise OCRCaptureError("OCR 用画像をデコードできませんでした。")
        return cg_image

    @classmethod
    def _combine_observations(cls, observations: list[OCRTextObservation]) -> str:
        if not observations:
            return ""

        lines: list[_OCRLine] = []
        ordered = sorted(observations, key=lambda item: (-item.center_y, item.min_x))
        for observation in ordered:
            merged = False
            for line in lines:
                if line.can_merge(observation):
                    line.add(observation)
                    merged = True
                    break
            if not merged:
                lines.append(_OCRLine.from_observation(observation))

        rendered_lines: list[str] = []
        for line in sorted(lines, key=lambda item: -item.center_y):
            ordered_line = sorted(line.observations, key=lambda item: item.min_x)
            joined = " ".join(item.text for item in ordered_line).strip()
            joined = re.sub(r"\s+", " ", joined)
            if joined:
                rendered_lines.append(joined)
        return "\n".join(rendered_lines).strip()

    @staticmethod
    def _looks_like_cancel(stderr: str, capture_path: Path) -> bool:
        lower = stderr.lower()
        if "cancel" in lower:
            return True
        return not stderr and (
            not capture_path.exists() or capture_path.stat().st_size == 0
        )

    @staticmethod
    def _looks_like_permission_error(stderr: str) -> bool:
        lower = stderr.lower()
        keywords = [
            "screen recording",
            "not authorized",
            "not permitted",
            "permission denied",
            "denied",
        ]
        return any(keyword in lower for keyword in keywords)
