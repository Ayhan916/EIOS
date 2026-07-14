"use client";

import { useCallback, useRef, useState } from "react";
const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type VoiceStatus = "idle" | "recording" | "transcribing" | "error";

interface UseVoiceInputResult {
  status: VoiceStatus;
  start: () => void;
  stop: () => void;
  cancel: () => void;
  errorMessage: string | null;
}

export function useVoiceInput(onTranscript: (text: string) => void): UseVoiceInputResult {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  // Cancel everything immediately — works from any state
  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.onstop = null; // prevent onstop from firing
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;

    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;

    chunksRef.current = [];
    setStatus("idle");
    setErrorMessage(null);
  }, []);

  const stop = useCallback(() => {
    // If transcribing, abort the API call instead
    if (abortRef.current) {
      cancel();
      return;
    }
    mediaRecorderRef.current?.stop();
  }, [cancel]);

  const start = useCallback(async () => {
    setErrorMessage(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMessage("Mikrofon nicht verfügbar in diesem Browser.");
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
      return;
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setErrorMessage("Mikrofon-Zugriff verweigert. Bitte Berechtigung erteilen.");
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
      return;
    }

    streamRef.current = stream;
    chunksRef.current = [];

    // Safari only supports audio/mp4; Chrome/Firefox prefer audio/webm;codecs=opus
    const MIME_CANDIDATES = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ];
    const mimeType = MIME_CANDIDATES.find((t) => MediaRecorder.isTypeSupported(t));

    const recorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream);
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setStatus("transcribing");

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const audioBlob = mimeType
          ? new Blob(chunksRef.current, { type: mimeType })
          : new Blob(chunksRef.current);
        chunksRef.current = [];

        const formData = new FormData();
        const ext = mimeType?.includes("mp4") ? "recording.mp4" : "recording.webm";
        formData.append("file", audioBlob, ext);

        const token = typeof window !== "undefined"
          ? localStorage.getItem("eios_access_token")
          : null;

        // Use fetch (not Axios) — fetch sets multipart boundary correctly
        const res = await fetch(
          `${BACKEND}/api/v1/copilot/transcribe?language=de`,
          {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
            signal: controller.signal,
          },
        );

        abortRef.current = null;

        if (!res.ok) {
          const detail = await res.text();
          throw new Error(`${res.status}: ${detail}`);
        }

        const data = await res.json() as { text: string };
        const text = data.text?.trim();
        if (text) onTranscript(text);
        setStatus("idle");
      } catch (err: unknown) {
        abortRef.current = null;
        if ((err as { name?: string })?.name === "CanceledError" || (err as { name?: string })?.name === "AbortError") {
          setStatus("idle");
          return;
        }
        console.error("Whisper transcription error:", err);
        setErrorMessage("Transkription fehlgeschlagen. Backend gestartet?");
        setStatus("error");
        setTimeout(() => { setStatus("idle"); setErrorMessage(null); }, 4000);
      }
    };

    recorder.start();
    setStatus("recording");
  }, [onTranscript]);

  return { status, start, stop, cancel, errorMessage };
}
