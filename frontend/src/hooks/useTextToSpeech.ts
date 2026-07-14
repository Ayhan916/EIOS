"use client";

import { useCallback, useRef, useState } from "react";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type TtsStatus = "idle" | "loading" | "playing" | "error";

interface UseTextToSpeechResult {
  speak: (text: string) => Promise<void>;
  stop: () => void;
  status: TtsStatus;
}

export function useTextToSpeech(): UseTextToSpeechResult {
  const [status, setStatus] = useState<TtsStatus>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    setStatus("idle");
  }, []);

  const speak = useCallback(async (text: string) => {
    stop();
    if (!text.trim()) return;

    setStatus("loading");
    const controller = new AbortController();
    abortRef.current = controller;

    const token = typeof window !== "undefined"
      ? localStorage.getItem("eios_access_token")
      : null;

    try {
      const res = await fetch(`${BACKEND}/api/v1/copilot/synthesize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`TTS ${res.status}`);

      const arrayBuffer = await res.arrayBuffer();
      abortRef.current = null;

      // Use AudioContext for reliable cross-browser playback (bypasses autoplay)
      const AudioContextCtor =
        (window as unknown as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext }).AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

      if (!AudioContextCtor) throw new Error("AudioContext not supported");

      const ctx = new AudioContextCtor();
      if (ctx.state === "suspended") await ctx.resume();

      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      setStatus("playing");
      source.onended = () => {
        setStatus("idle");
        ctx.close();
      };
      source.start(0);
    } catch (err: unknown) {
      abortRef.current = null;
      if ((err as { name?: string })?.name === "AbortError") {
        setStatus("idle");
        return;
      }
      console.error("TTS error:", err);
      setStatus("error");
      setTimeout(() => setStatus("idle"), 2000);
    }
  }, [stop]);

  return { speak, stop, status };
}
