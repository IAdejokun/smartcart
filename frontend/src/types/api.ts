// API types — mirrors backend Pydantic schemas in app/schemas/.
// These types are the single source of truth for the frontend; if the backend
// schemas change, these change in lockstep (in a future iteration we'd auto-generate
// these from the OpenAPI spec, but hand-keeping them at MVP scale is fine).

export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ProductSummary {
  id: string;
  asin: string;
  title: string;
  category: string;
  price: number | string;
  avg_rating: number;
  review_count: number;
  // Optional — backend includes this on recommendation responses and product
  // detail, but trims it on bulk product list endpoints to keep payload small.
  extra_data?: {
    image_url?: string | null;
    store?: string | null;
    main_category?: string | null;
    features?: string[];
    description?: string[];
  };
}


export interface ProductDetail extends ProductSummary {
  extra_data: {
    image_url?: string | null;
    store?: string | null;
    main_category?: string | null;
    features?: string[];
    description?: string[];
  };
}

export interface ProductListResponse {
  items: ProductSummary[];
  total: number;
  page: number;
  page_size: number;
}

// Recommendation context — mirrors RecommendationContext in app/schemas/cart.py
export interface RecommendationContext {
  policy: "drl" | "collab_filter" | "organic";
  model_id: string | null;
  recommendation_rank: number | null;
  shown_products: string[];
  session_state_snapshot: Record<string, unknown>;
}

export interface RecommendationItem {
  product: ProductSummary;
  rank: number;
  q_value: number | null;
}

export interface RecommendationResponse {
  policy: "drl" | "collab_filter" | "organic";
  model_id: string | null;
  items: RecommendationItem[];
  session_state_snapshot: Record<string, unknown>;
}

export interface CartItem {
  product_id: string;
  title: string;
  price: number;
  quantity: number;
}

export interface CartResponse {
  items: CartItem[];
  item_count: number;
  subtotal: number;
}

// Telemetry — mirrors app/services/telemetry_service.py outputs
export interface ConversionRow {
  policy: string;
  shown: number;
  converted: number;
  rate: number;
}

export interface AvgRewardRow {
  policy: string;
  avg_reward: number;
  n_episodes: number;
}

export interface EntropyPoint {
  bucket_start: string | null;
  distinct_top_products: number;
  n_events: number;
  entropy_proxy: number;
}

export interface EpsilonPoint {
  version: string;
  steps_done: number;
  epsilon: number;
  trained_at: string | null;
}

export interface TelemetrySummary {
  window: string;
  computed_at: string;
  conversion_by_policy: ConversionRow[];
  avg_reward_by_policy: AvgRewardRow[];
  q_value_entropy_timeline: EntropyPoint[];
  epsilon_curve: EpsilonPoint[];
}

export interface PolicyComparison {
  window: string;
  policies: {
    drl: {
      shown: number;
      converted: number;
      rate: number;
      avg_reward: number;
      n_episodes: number;
    };
    collab_filter: {
      shown: number;
      converted: number;
      rate: number;
      avg_reward: number;
      n_episodes: number;
    };
  };
}
