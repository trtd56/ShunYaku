from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shunyaku.ocr import (
    OCRNoTextError,
    OCRPermissionError,
    OCRTextObservation,
    ScreenOCR,
)


class ScreenOCRTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ocr = ScreenOCR()

    def tearDown(self) -> None:
        self.ocr.shutdown()

    def test_capture_text_returns_none_when_selection_is_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            capture_path = Path(temp_dir) / "capture.png"
            capture_path.touch()

            with patch.object(self.ocr, "_create_capture_path", return_value=capture_path):
                with patch.object(
                    self.ocr,
                    "_run_screencapture",
                    return_value=subprocess.CompletedProcess(
                        args=["screencapture"],
                        returncode=1,
                        stdout="",
                        stderr="",
                    ),
                ):
                    result = self.ocr.capture_text()

            self.assertIsNone(result)
            self.assertFalse(capture_path.exists())

    def test_capture_text_cleans_up_temp_file_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            capture_path = Path(temp_dir) / "capture.png"
            capture_path.write_bytes(b"fake-png")

            with patch.object(self.ocr, "_create_capture_path", return_value=capture_path):
                with patch.object(self.ocr, "_capture_image", return_value=True):
                    with patch.object(
                        self.ocr,
                        "_extract_text_from_capture",
                        return_value="HELLO WORLD",
                    ):
                        result = self.ocr.capture_text()

            self.assertEqual(result, "HELLO WORLD")
            self.assertFalse(capture_path.exists())

    def test_capture_image_maps_permission_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            capture_path = Path(temp_dir) / "capture.png"
            capture_path.touch()

            with patch.object(
                self.ocr,
                "_run_screencapture",
                return_value=subprocess.CompletedProcess(
                    args=["screencapture"],
                    returncode=1,
                    stdout="",
                    stderr="User is not authorized for screen recording",
                ),
            ):
                with self.assertRaises(OCRPermissionError):
                    self.ocr._capture_image(capture_path)

    def test_extract_text_raises_when_no_text_is_found(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            capture_path = Path(temp_dir) / "capture.png"
            capture_path.write_bytes(b"fake-png")

            with patch.object(self.ocr, "_recognize_text", return_value=[]):
                with self.assertRaises(OCRNoTextError):
                    self.ocr._extract_text_from_capture(capture_path)

    def test_combine_observations_orders_top_to_bottom_then_left_to_right(self) -> None:
        observations = [
            OCRTextObservation(
                text="Bottom",
                min_x=0.1,
                min_y=0.10,
                width=0.2,
                height=0.05,
            ),
            OCRTextObservation(
                text="Right",
                min_x=0.52,
                min_y=0.71,
                width=0.2,
                height=0.05,
            ),
            OCRTextObservation(
                text="Left",
                min_x=0.08,
                min_y=0.70,
                width=0.2,
                height=0.05,
            ),
        ]

        combined = ScreenOCR._combine_observations(observations)

        self.assertEqual(combined, "Left Right\nBottom")


if __name__ == "__main__":
    unittest.main()
