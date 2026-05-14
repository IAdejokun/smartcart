import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addToCart, getCart, removeFromCart } from "../api/cart";
import { useAuthStore } from "../store/authStore";
import { useSessionStore } from "../store/sessionStore";
import type { RecommendationContext } from "../types/api";

const CART_KEY = ["cart"];

export function useCart() {
  const accessToken = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: CART_KEY,
    queryFn: getCart,
    enabled: Boolean(accessToken),
    staleTime: 10_000,
  });
}

export function useAddToCart() {
  const queryClient = useQueryClient();
  const sessionId = useSessionStore((s) => s.sessionId);

  return useMutation({
    mutationFn: (args: {
      product_id: string;
      quantity?: number;
      recommendation_context: RecommendationContext;
    }) =>
      addToCart({
        product_id: args.product_id,
        quantity: args.quantity ?? 1,
        session_id: sessionId,
        recommendation_context: args.recommendation_context,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CART_KEY });
      // Also invalidate recommendations — adding to cart changes user state vector
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
}

export function useRemoveFromCart() {
  const queryClient = useQueryClient();
  const sessionId = useSessionStore((s) => s.sessionId);

  return useMutation({
    mutationFn: (productId: string) =>
      removeFromCart({ product_id: productId, session_id: sessionId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CART_KEY });
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
}
