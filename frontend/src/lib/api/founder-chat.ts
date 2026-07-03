import apiClient from "./client";

export interface FounderChatResponse {
  conversation_id: string;
  answer: string;
  model_used: string;
  generation_ms: number | null;
  context_available: boolean;
  quick_actions: string[];
}

export interface FounderChatRequest {
  question: string;
  conversation_id?: string;
  window_days?: number;
}

export const founderChatApi = {
  ask: async (body: FounderChatRequest): Promise<FounderChatResponse> => {
    const res = await apiClient.post("/copilot/founder", body);
    return res.data;
  },
};

export const FOUNDER_QUICK_ACTIONS = [
  "Wie ist der aktuelle Platform Health Score?",
  "Warum hat sich die Accuracy verschlechtert?",
  "Welches Modul performt am schlechtesten?",
  "Was sollte als nächstes verbessert werden?",
  "Welche Agents haben Fehler?",
  "Wie hoch sind die API-Kosten dieser Woche?",
];
