import { keepPreviousData, useQuery } from "@tanstack/react-query";
import * as api from "./client";
import type { SimilarParams } from "./client";

export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: api.getCategories });
}

export function useProducts(params: { product_type?: string; collection?: string }) {
  return useQuery({
    queryKey: ["products", params],
    queryFn: () => api.getProducts(params),
    placeholderData: keepPreviousData,
  });
}

export function useProduct(sku: string | undefined) {
  return useQuery({
    queryKey: ["product", sku],
    queryFn: () => api.getProduct(sku as string),
    enabled: sku !== undefined,
  });
}

export function useSimilar(sku: string | undefined, params: SimilarParams) {
  return useQuery({
    queryKey: ["similar", sku, params],
    queryFn: () => api.getSimilar(sku as string, params),
    enabled: sku !== undefined,
    // §10.1: "so lists don't flash while weights change" — keep the last
    // result on screen while the debounced re-fetch for new weights lands.
    placeholderData: keepPreviousData,
  });
}

export function useVersion() {
  return useQuery({ queryKey: ["version"], queryFn: api.getVersion });
}

export function useEvalReport() {
  return useQuery({ queryKey: ["evalReport"], queryFn: api.getEvalReport });
}
