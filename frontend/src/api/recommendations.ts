import { apiClient } from "./client";
import type { RecommendationResponse } from "../types/api";

export async function getRecommendations(args: {
  session_id: string;
  top_k?: number;
}): Promise<RecommendationResponse> {
  const response = await apiClient.get<RecommendationResponse>(
    "/recommendations",
    {
      params: args,
    },
  );
  return response.data;
}
