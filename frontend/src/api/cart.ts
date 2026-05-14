import { apiClient } from "./client";
import type { CartResponse, RecommendationContext } from "../types/api";

export async function getCart(): Promise<CartResponse> {
  const response = await apiClient.get<CartResponse>("/cart");
  return response.data;
}

export async function addToCart(args: {
  product_id: string;
  quantity: number;
  session_id: string;
  recommendation_context: RecommendationContext;
}): Promise<CartResponse> {
  const response = await apiClient.post<CartResponse>("/cart/add", args);
  return response.data;
}

export async function removeFromCart(args: {
  product_id: string;
  session_id: string;
}): Promise<CartResponse> {
  const response = await apiClient.post<CartResponse>("/cart/remove", args);
  return response.data;
}
