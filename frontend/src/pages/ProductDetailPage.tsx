import { useParams, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { StarIcon } from "@heroicons/react/24/solid";
import { getProduct } from "../api/products";
import { useAddToCart } from "../hooks/useCart";
import { formatPrice } from "../lib/format";
import { PolicyBadge } from "../components/recommendations/PolicyBadge";
import type { RecommendationContext } from "../types/api";

export default function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const location = useLocation();
  const addToCart = useAddToCart();

  // Recommendation context propagated from the previous page (e.g. the recs carousel).
  // null if the user navigated here directly, deep-linked, or came from the
  // storefront grid (none of which carry a recommendation context).
  const incomingContext =
    (location.state as { recommendationContext?: RecommendationContext } | null)
      ?.recommendationContext ?? null;

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => getProduct(productId!),
    enabled: Boolean(productId),
  });

  if (isLoading || !product) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="bg-gray-100 rounded-2xl h-96 animate-pulse" />
      </div>
    );
  }

  const imageUrl = product.extra_data?.image_url;
  const features = product.extra_data?.features ?? [];

  function handleAdd() {
    addToCart.mutate({
      product_id: product!.id,
      // If we got here from a recommendation, the carousel's context flows
      // through. Otherwise the add is genuinely organic — direct nav, share
      // link, or browsing the catalogue grid.
      recommendation_context: incomingContext ?? {
        policy: "organic",
        model_id: null,
        recommendation_rank: null,
        shown_products: [],
        session_state_snapshot: {},
      },
    });
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="grid md:grid-cols-2 gap-8 bg-white rounded-2xl p-6 border border-gray-200">
        <div className="aspect-square bg-gray-50 rounded-xl grid place-items-center overflow-hidden">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={product.title}
              className="w-full h-full object-contain p-6"
            />
          ) : (
            <span className="text-gray-400 text-sm">No image available</span>
          )}
        </div>

        <div className="flex flex-col">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs uppercase tracking-wide text-gray-500 font-medium">
              {product.category.replace(/_/g, " ")}
            </span>
            {/* Show the attribution badge when the user arrived from a recommendation —
                helps them see the system is tracking the path coherently. */}
            {incomingContext && incomingContext.policy !== "organic" && (
              <PolicyBadge policy={incomingContext.policy} />
            )}
          </div>

          <h1 className="text-2xl font-semibold text-gray-900 mb-3">
            {product.title}
          </h1>

          <div className="flex items-center gap-2 text-sm text-gray-600 mb-4">
            <StarIcon className="w-4 h-4 text-amber-400" />
            <span className="font-medium">{product.avg_rating.toFixed(1)}</span>
            <span>·</span>
            <span>{product.review_count.toLocaleString()} reviews</span>
          </div>

          <div className="text-3xl font-semibold mb-6">
            {formatPrice(product.price)}
          </div>

          {features.length > 0 && (
            <ul className="text-sm text-gray-700 space-y-1.5 mb-6 list-disc pl-4">
              {features.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}

          <button
            onClick={handleAdd}
            disabled={addToCart.isPending}
            className="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium py-3 rounded-lg transition mt-auto"
          >
            {addToCart.isPending ? "Adding…" : "Add to cart"}
          </button>
        </div>
      </div>
    </div>
  );
}
