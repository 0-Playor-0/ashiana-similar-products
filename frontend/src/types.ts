export interface Product {
  sku: string;
  title: string;
  product_type: string;
  collection: string | null;
  price_inr: number | null;
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
