"use client";

import { useEffect } from "react";

export default function ReviewError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("[Review Error]", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="bg-white rounded-2xl border border-red-200 shadow-sm max-w-2xl w-full p-6">
        <h1 className="text-lg font-bold text-red-600 mb-2">Fehler beim Laden der Review-Seite</h1>
        <p className="text-sm text-gray-600 mb-4">Bitte teile diesen Fehler zur Diagnose:</p>
        <pre className="bg-red-50 border border-red-100 rounded-lg p-4 text-xs text-red-800 whitespace-pre-wrap overflow-auto max-h-64 font-mono">
          {error.message}
          {"\n\n"}
          {error.stack}
        </pre>
        <button
          onClick={reset}
          className="mt-4 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          Erneut versuchen
        </button>
      </div>
    </div>
  );
}
