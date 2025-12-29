from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import sys
from collections.abc import Mapping
from collections.abc import Sequence


class OcrNotAvailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PaddleOcrConfig:
    lang: str = "german"
    use_angle_cls: bool = True


def ocr_image_path(image_path: Path, *, config: PaddleOcrConfig | None = None) -> str:
    if not image_path.exists():
        raise FileNotFoundError(str(image_path))

    cfg = config or PaddleOcrConfig()
    ocr = _get_ocr(cfg.lang, cfg.use_angle_cls)

    try:
        result = _predict(ocr, str(image_path), use_angle_cls=cfg.use_angle_cls)
    except Exception as exc:
        raise RuntimeError(f"PaddleOCR failed: {exc}") from exc

    lines = _flatten_and_sort(result)
    return "\n".join(lines).strip()


def _flatten_and_sort(result: object) -> list[str]:
    # PaddleOCR returns either:
    # - list[list[[box, (text, score)], ...]] for multiple images
    # - list[[box, (text, score)], ...] for single image (depending on version)
    if not isinstance(result, list):
        return []

    entries: list[tuple[float, float, str]] = []

    # Newer PaddleOCR (PaddleX pipeline) returns a list of OCRResult (dict-like)
    # with fields like rec_texts + rec_boxes.
    if result and isinstance(result[0], Mapping) and "rec_texts" in result[0]:
        for page in result:
            if not isinstance(page, Mapping):
                continue
            texts = page.get("rec_texts")
            if not isinstance(texts, list):
                continue
            boxes = page.get("rec_boxes")
            if boxes is None:
                boxes = page.get("dt_polys")

            for idx, text in enumerate(texts):
                s = str(text).strip()
                if not s:
                    continue
                box = None
                if (
                    boxes is not None
                    and not isinstance(boxes, (str, bytes))
                    and hasattr(boxes, "__len__")
                    and hasattr(boxes, "__getitem__")
                    and idx < len(boxes)
                ):
                    box = boxes[idx]
                x, y = _top_left_xy(box)
                entries.append((y, x, s))
        entries.sort(key=lambda t: (t[0], t[1]))
        return [t[2] for t in entries]

    def ingest_item(item: object) -> None:
        if not (isinstance(item, list) and len(item) >= 2):
            return
        box = item[0]
        text_tuple = item[1]
        if not (isinstance(text_tuple, (list, tuple)) and len(text_tuple) >= 1):
            return
        text = str(text_tuple[0]).strip()
        if not text:
            return

        x, y = _top_left_xy(box)
        entries.append((y, x, text))

    # Handle nested results
    if result and isinstance(result[0], list) and result and result and _looks_like_item(result[0]):
        for item in result:
            ingest_item(item)
    else:
        for maybe_image in result:
            if isinstance(maybe_image, list):
                for item in maybe_image:
                    ingest_item(item)

    entries.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in entries]


def _looks_like_item(value: object) -> bool:
    return isinstance(value, list) and len(value) >= 2 and isinstance(value[0], (list, tuple))


def _top_left_xy(box: object) -> tuple[float, float]:
    # box is typically [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    try:
        if isinstance(box, Sequence) and not isinstance(box, (str, bytes)) and len(box) == 4 and all(
            isinstance(v, (int, float)) for v in box
        ):
            return float(box[0]), float(box[1])
        if isinstance(box, Sequence) and not isinstance(box, (str, bytes)) and len(box) > 0:
            pt = box[0]
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                return float(pt[0]), float(pt[1])
    except Exception:
        pass
    return 0.0, 0.0


@lru_cache(maxsize=4)
def _get_ocr(lang: str, use_angle_cls: bool):
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as exc:
        raise OcrNotAvailableError(
            "PaddleOCR is not installed/available. Install it in this environment to enable image OCR."
        ) from exc

    try:
        import paddle  # type: ignore  # noqa: F401
    except Exception as exc:
        raise OcrNotAvailableError(
            "PaddleOCR backend requires PaddlePaddle (`paddle`). "
            f"Current Python is {sys.version.split()[0]}; PaddlePaddle wheels may not be available for this version. "
            "Use Python 3.11/3.12 (or a conda env) and install `paddlepaddle` + `paddleocr`."
        ) from exc

    # PaddleOCR's constructor args vary across versions (and some versions raise ValueError on unknown args).
    # Try the most capable setup first, then fall back.
    try:
        return PaddleOCR(lang=lang, use_textline_orientation=use_angle_cls)
    except Exception:
        pass
    try:
        return PaddleOCR(lang=lang, use_angle_cls=use_angle_cls)
    except Exception:
        pass
    return PaddleOCR(lang=lang)


def _predict(ocr, image_path: str, *, use_angle_cls: bool) -> object:
    # PaddleOCR APIs vary:
    # - older: ocr.ocr(img, cls=bool)
    # - newer: ocr.ocr delegates to predict(img) without cls
    if hasattr(ocr, "predict"):
        try:
            return ocr.predict(image_path)
        except TypeError:
            return ocr.predict(image_path)

    if hasattr(ocr, "ocr"):
        try:
            return ocr.ocr(image_path, cls=use_angle_cls)
        except TypeError:
            return ocr.ocr(image_path)

    raise RuntimeError("Unsupported PaddleOCR object: missing predict/ocr methods")
