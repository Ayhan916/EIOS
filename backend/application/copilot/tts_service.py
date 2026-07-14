"""
Offline Text-to-Speech using Piper TTS (Mozilla, MIT licence).

Voice model: de_DE-thorsten-medium (~63 MB, 22 050 Hz, neural)
Model is loaded once per process and kept in RAM.
"""
from __future__ import annotations

import io
import logging
import threading
import wave

logger = logging.getLogger(__name__)

_MODEL_PATH = "/Users/ayhanyaman/.local/share/piper-voices/de_DE-thorsten-medium.onnx"
_lock = threading.Lock()
_voice = None


def _get_voice():
    global _voice
    if _voice is None:
        with _lock:
            if _voice is None:
                from piper.voice import PiperVoice
                logger.info("Loading Piper TTS voice model (first call — cached afterwards)")
                _voice = PiperVoice.load(_MODEL_PATH)
                logger.info("Piper TTS voice ready (sample_rate=%d)", _voice.config.sample_rate)
    return _voice


def synthesize(text: str) -> bytes:
    """Convert text to WAV audio bytes using Piper TTS."""
    voice = _get_voice()

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        voice.synthesize_wav(text, wf)

    buf.seek(0)
    return buf.read()
