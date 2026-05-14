import { SparklesIcon } from "@heroicons/react/24/outline";
import { useRecommendations } from "../../hooks/useRecommendations";
import { ProductCard } from "../storefront/ProductCard";
import type { RecommendationContext } from "../../types/api";

export function RecommendationCarousel() {
  const { data, isLoading, isError } = useRecommendations(5);

  if (isLoading) {
    return (
      <section className="bg-gradient-to-br from-brand-50 to-amber-50 rounded-2xl p-6 mb-8">
        <h2 className="text-lg font-semibold mb-4">Recommended for you</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="aspect-square bg-white/60 rounded-xl animate-pulse"
            />
          ))}
        </div>
      </section>
    );
  }

  if (isError || !data || data.items.length === 0) {
    return null;
  }

  return (
    <section className="bg-gradient-to-br from-brand-50 to-amber-50 rounded-2xl p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <SparklesIcon className="w-5 h-5 text-brand-600" />
          Recommended for you
        </h2>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {data.items.map((item) => {
          const context: RecommendationContext = {
            policy: data.policy,
            model_id: data.model_id,
            recommendation_rank: item.rank,
            shown_products: data.items.map((i) => i.product.id),
            session_state_snapshot: data.session_state_snapshot,
          };

          const imageUrl = item.product.extra_data?.image_url ?? null;

          return (
            <ProductCard
              key={item.product.id}
              product={item.product}
              imageUrl={imageUrl}
              recommendationContext={context}
              policyBadge={data.policy}
            />
          );
        })}
      </div>
    </section>
  );
}
