"""
Offline speech-to-text using faster-whisper (CTranslate2 backend).

Model is loaded once per process (singleton) and kept in RAM.
Default: whisper-tiny — ~40 MB, fast, good quality for DE/EN.
Upgrade to "base" or "small" for higher accuracy if hardware allows.
"""
from __future__ import annotations

import io
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model: Optional[object] = None
_MODEL_SIZE = "tiny"
_DEVICE = "cpu"
_COMPUTE_TYPE = "int8"


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from faster_whisper import WhisperModel
                logger.info("Loading Whisper model '%s' (first call — cached afterwards)", _MODEL_SIZE)
                _model = WhisperModel(_MODEL_SIZE, device=_DEVICE, compute_type=_COMPUTE_TYPE)
                logger.info("Whisper model ready")
    return _model


def transcribe(audio_bytes: bytes, language: str = "de") -> str:
    """Transcribe raw audio bytes (webm/wav/mp4). Returns the transcript string."""
    model = _get_model()
    audio_file = io.BytesIO(audio_bytes)

    segments, info = model.transcribe(
        audio_file,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )

    logger.debug(
        "Whisper detected language '%s' (probability %.2f)",
        info.language,
        info.language_probability,
    )

    text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
    return text
