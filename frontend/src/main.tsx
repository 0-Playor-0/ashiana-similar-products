import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./styles/tokens.css";
import "./index.css";
import App from "./App.tsx";
import Label from "./routes/Label.tsx";

const queryClient = new QueryClient();
const labelingEnabled = import.meta.env.VITE_ENABLE_LABELING === "true";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          {labelingEnabled && <Route path="/label" element={<Label />} />}
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
