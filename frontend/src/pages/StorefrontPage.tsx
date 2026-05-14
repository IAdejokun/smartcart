import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listProducts, listCategories } from "../api/products";
import { ProductCard } from "../components/storefront/ProductCard";
import { RecommendationCarousel } from "../components/recommendations/RecommendationCarousel";
import { cn } from "../lib/cn";

export default function StorefrontPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
    staleTime: 5 * 60 * 1000,
  });

  const { data: productList, isLoading } = useQuery({
    queryKey: ["products", { search, category, page }],
    queryFn: () =>
      listProducts({
        search: search.length >= 2 ? search : undefined,
        category,
        page,
        page_size: 24,
      }),
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <RecommendationCarousel />

      <div className="flex flex-col md:flex-row gap-3 mb-6">
        <input
          type="text"
          placeholder="Search products…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
        />

        <div className="flex gap-2 overflow-x-auto pb-1">
          <CategoryChip
            label="All"
            active={!category}
            onClick={() => {
              setCategory(undefined);
              setPage(1);
            }}
          />
          {categories?.map((c) => (
            <CategoryChip
              key={c}
              label={c.replace(/_/g, " ")}
              active={category === c}
              onClick={() => {
                setCategory(c);
                setPage(1);
              }}
            />
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="aspect-[3/4] bg-white rounded-xl animate-pulse"
            />
          ))}
        </div>
      )}

      {productList && productList.items.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          No products match your filters.
        </div>
      )}

      {productList && productList.items.length > 0 && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {productList.items.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                imageUrl={p.extra_data?.image_url ?? null}
              />
            ))}
          </div>

          <Pagination
            page={productList.page}
            pageSize={productList.page_size}
            total={productList.total}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}

function CategoryChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "whitespace-nowrap px-4 py-2 text-sm font-medium rounded-lg border transition",
        active
          ? "bg-brand-600 text-white border-brand-600"
          : "bg-white text-gray-700 border-gray-200 hover:border-gray-300",
      )}
    >
      {label}
    </button>
  );
}

function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between mt-8 text-sm">
      <span className="text-gray-500">
        Page {page} of {totalPages} · {total.toLocaleString()} products
      </span>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="px-3 py-1.5 rounded-lg border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
        >
          Previous
        </button>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="px-3 py-1.5 rounded-lg border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
