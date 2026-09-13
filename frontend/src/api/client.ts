// Thin fetch wrapper for the FastAPI service (§9). No client-side ranking
// logic lives here or anywhere else in the frontend — every score, filter,
// and reason string is computed server-side and just rendered.
import type {
  CategoriesResponse,
  EvalReport,
  ProductDetail,
  ProductSummary,
  SimilarResponse,
  VersionResponse,
} from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

function buildUrl(path: string, params?: object): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function request<T>(path: string, params?: object): Promise<T> {
  const res = await fetch(buildUrl(path, params));
  if (!res.ok) {
    let detail = res.statusText || `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // response body wasn't JSON — keep the statusText fallback
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export function getHealth(signal?: AbortSignal): Promise<{ status: string }> {
  return fetch(buildUrl("/health"), { signal }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, res.statusText);
    return res.json();
  });
}

export function getVersion(): Promise<VersionResponse> {
  return request("/version");
}

export function getCategories(): Promise<CategoriesResponse> {
  return request("/categories");
}

export function getProducts(params: {
  product_type?: string;
  collection?: string;
}): Promise<ProductSummary[]> {
  return request("/products", params);
}

export function getProduct(sku: string): Promise<ProductDetail> {
  return request(`/products/${encodeURIComponent(sku)}`);
}

export interface SimilarParams {
  k?: number;
  w_image?: number;
  w_text?: number;
  w_meta?: number;
  same_category?: boolean;
  max_price_ratio?: number;
}

export function getSimilar(sku: string, params: SimilarParams): Promise<SimilarResponse> {
  return request(`/products/${encodeURIComponent(sku)}/similar`, params);
}

export function getEvalReport(): Promise<EvalReport> {
  return request("/eval/report");
}

// ProductSummary.thumb_url is API-relative (e.g. "/thumbs/{sku}.webp", §9) —
// resolve it against the API origin, not the frontend's own origin, since
// they're served from different ports/hosts in dev and (per render.yaml,
// Phase 8) different services in production.
export function resolveThumbUrl(thumbUrl: string): string {
  return thumbUrl.startsWith("/") ? `${API_BASE_URL}${thumbUrl}` : thumbUrl;
}
