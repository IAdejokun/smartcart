import { useQuery } from "@tanstack/react-query";
import { getRecommendations } from "../api/recommendations";
import { useSessionStore } from "../store/sessionStore";

export function useRecommendations(topK: number = 5) {
  const sessionId = useSessionStore((s) => s.sessionId);
  return useQuery({
    queryKey: ["recommendations", sessionId, topK],
    queryFn: () => getRecommendations({ session_id: sessionId, top_k: topK }),
    staleTime: 15_000,
  });
}
