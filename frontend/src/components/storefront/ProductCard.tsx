import { Link } from "react-router-dom";
import { StarIcon } from "@heroicons/react/24/solid";
import { useAddToCart } from "../../hooks/useCart";
import { formatPrice } from "../../lib/format";
import { PolicyBadge } from "../recommendations/PolicyBadge";
import { cn } from "../../lib/cn";
import type { ProductSummary, RecommendationContext } from "../../types/api";

interface ProductCardProps {
  product: ProductSummary;
  imageUrl?: string | null;
  recommendationContext?: RecommendationContext;
  policyBadge?: "drl" | "collab_filter" | "organic";
}

export function ProductCard({
  product,
  imageUrl,
  recommendationContext,
  policyBadge,
}: ProductCardProps) {
  const addToCart = useAddToCart();

  function handleAdd(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    addToCart.mutate({
      product_id: product.id,
      recommendation_context: recommendationContext ?? {
        policy: "organic",
        model_id: null,
        recommendation_rank: null,
        shown_products: [],
        session_state_snapshot: {},
      },
    });
  }

  return (
    <Link
      to={`/products/${product.id}`}
      // Pass recommendation context through navigation. The detail page reads it
      // from location.state to preserve attribution if the user adds from there.
      state={recommendationContext ? { recommendationContext } : undefined}
      className="group bg-white rounded-xl border border-gray-200 hover:border-brand-300 hover:shadow-md transition overflow-hidden flex flex-col"
    >
      <div className="aspect-square bg-gray-100 grid place-items-center overflow-hidden">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={product.title}
            className="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform"
            loading="lazy"
          />
        ) : (
          <span className="text-gray-400 text-xs">No image</span>
        )}
      </div>

      <div className="p-3 flex-1 flex flex-col">
        <div className="flex items-start justify-between gap-2 mb-1">
          <span className="text-[10px] uppercase tracking-wide text-gray-500 font-medium">
            {product.category.replace(/_/g, " ")}
          </span>
          {policyBadge && <PolicyBadge policy={policyBadge} />}
        </div>

        <h3 className="text-sm font-medium text-gray-900 line-clamp-2 mb-2 leading-snug">
          {product.title}
        </h3>

        <div className="flex items-center gap-1 text-xs text-gray-500 mb-3">
          <StarIcon className="w-3.5 h-3.5 text-amber-400" />
          <span>{product.avg_rating.toFixed(1)}</span>
          <span>·</span>
          <span>{product.review_count.toLocaleString()} reviews</span>
        </div>

        <div className="mt-auto flex items-center justify-between">
          <span className="font-semibold text-gray-900">
            {formatPrice(product.price)}
          </span>
          <button
            onClick={handleAdd}
            disabled={addToCart.isPending}
            className={cn(
              "text-xs font-medium px-3 py-1.5 rounded-lg transition",
              "bg-brand-600 hover:bg-brand-700 text-white disabled:opacity-50",
            )}
          >
            {addToCart.isPending ? "…" : "Add"}
          </button>
        </div>
      </div>
    </Link>
  );
}
