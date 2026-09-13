import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./styles/tokens.css";
import "./index.css";
import Layout from "./components/Layout";
import CatalogPage from "./routes/CatalogPage";
import ProductPage from "./routes/ProductPage";
import { ApiError } from "./api/client";

// Recharts is a large dependency used only on this one page — code-split it
// so the catalog/product pages (the demo's main path) stay light.
const UnderTheHood = lazy(() => import("./routes/UnderTheHood"));
const Label = lazy(() => import("./routes/Label.tsx"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // A free-tier API can be cold-starting for up to about a minute
      // (§10.3), so retry network/5xx failures generously with backoff
      // rather than giving up after react-query's default 3 quick
      // attempts. A 4xx (404 unknown sku, 422 bad params) is a permanent,
      // deterministic failure — retrying it would just delay the error
      // state for no benefit, so those fail immediately.
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 5;
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
    },
  },
});
const labelingEnabled = import.meta.env.VITE_ENABLE_LABELING === "true";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<CatalogPage />} />
            <Route path="/p/:sku" element={<ProductPage />} />
            <Route
              path="/under-the-hood"
              element={
                <Suspense fallback={<p>Loading…</p>}>
                  <UnderTheHood />
                </Suspense>
              }
            />
          </Route>
          {labelingEnabled && (
            <Route
              path="/label"
              element={
                <Suspense fallback={<p>Loading…</p>}>
                  <Label />
                </Suspense>
              }
            />
          )}
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
