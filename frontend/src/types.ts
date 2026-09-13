export interface Product {
  sku: string;
  title: string;
  product_type: string;
  collection: string | null;
  price_inr: number | null;
}

// --- API response types (api/app/models.py, §9) ---------------------------

export interface ProductSummary {
  sku: string;
  title: string;
  product_type: string;
  collection: string | null;
  price_inr: number | null;
  thumb_url: string;
}

export interface ProductDetail extends ProductSummary {
  descriptor_sentence: string | null;
  materials: string[];
  stones: string[];
  colors: string[];
  in_stock: boolean | null;
  attr_provenance: Record<string, string>;
}

export interface Weights {
  image: number;
  text: number;
  meta: number;
}

export interface SignalBreakdown {
  cosine: number;
  z: number;
  contribution: number;
}

export interface ItemBreakdown {
  image: SignalBreakdown;
  text: SignalBreakdown;
  meta: SignalBreakdown;
}

export interface SimilarItem {
  product: ProductSummary;
  score: number;
  breakdown: ItemBreakdown;
  reasons: string[];
  fallback: boolean;
}

export interface SimilarResponse {
  query_sku: string;
  bundle_version: string;
  weights_used: Weights;
  fallback_used: boolean;
  items: SimilarItem[];
}

export interface VersionResponse {
  bundle_version: string;
  models: Record<string, string>;
  default_weights: Weights;
  n_items: number;
}

export interface CategoriesResponse {
  product_types: { product_type: string; count: number }[];
  collections: { collection: string; count: number }[];
}

// --- Evaluation report (artifacts/eval/report.json, pipeline/evaluate.py) -

export interface MetricWithCI {
  mean: number;
  ci_low: number;
  ci_high: number;
}

export interface MethodMetric {
  ndcg_at_5: MetricWithCI;
  p_at_5: MetricWithCI;
}

export interface FailureCase {
  query_sku: string;
  query_title: string;
  ndcg_at_5: number;
  top5: { sku: string; title: string; label: number }[];
}

export interface EvalReport {
  n_queries: number;
  k: number;
  methods: Record<string, MethodMetric>;
  fused_vs_baseline: {
    fused_default_ndcg_at_5: number;
    same_type_nearest_price_ndcg_at_5: number;
    fused_beats_baseline: boolean;
    note: string;
  };
  weight_tuning: {
    grid_step: number;
    n_grid_points: number;
    best_single_point: { weights: [number, number, number]; mean_ndcg_at_5: number };
    tolerance_se: number;
    plateau_size: number;
    chosen_weights: Weights;
    chosen_weights_mean_ndcg_at_5: number;
    leave_one_query_out_ndcg_at_5: MetricWithCI;
  };
  proxies: {
    held_out_attribute_agreement: number | null;
    cross_signal_agreement_jaccard5: number;
    coverage: { share: number; n_unique_recommended: number; n_catalog: number };
    hubness: {
      mean_indegree: number;
      std_indegree: number;
      skewness: number;
      top_hubs: { sku: string; title: string; count: number }[];
    };
    diversity_mean_intra_list_similarity: number | null;
    price_sanity_median_ratio: number | null;
    image_augmentation_robustness: { hits: number; n_samples: number };
  };
  failure_cases: FailureCase[];
  methodology_notes: string[];
}

export interface LabelPoolEntry {
  query_sku: string;
  query_title: string;
  product_type: string;
  sources: Record<string, string[]>;
  pool: string[];
}

export type RelevanceLabel = 0 | 1 | 2;

export interface LabelRecord {
  query_sku: string;
  candidate_sku: string;
  label: RelevanceLabel;
  labeled_at: string;
}
