import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SessionState {
  sessionId: string;
  rotateSession: () => void;
}

function generateSessionId(): string {
  // crypto.randomUUID is available in all evergreen browsers
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `s_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      sessionId: generateSessionId(),
      rotateSession: () => set({ sessionId: generateSessionId() }),
    }),
    {
      name: "smartcart-session",
    },
  ),
);
