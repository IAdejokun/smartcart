import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Shell } from "./components/layout/Shell";
import { RouteGuard } from "./components/auth/RouteGuard";

// Lazy-loaded pages — each becomes a separate JS chunk
const LandingPage = lazy(() => import("./pages/LandingPage"));
const StorefrontPage = lazy(() => import("./pages/StorefrontPage"));
const ProductDetailPage = lazy(() => import("./pages/ProductDetailPage"));
const CartPage = lazy(() => import("./pages/CartPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function PageFallback() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-gray-400 text-sm">Loading…</div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route element={<Shell />}>
              {/* Landing — marketing front door (no auth required, no shell nav state) */}
              <Route index element={<LandingPage />} />

              {/* App routes — same structure as before, just no longer at root */}
              <Route path="shop" element={<StorefrontPage />} />
              <Route
                path="products/:productId"
                element={<ProductDetailPage />}
              />
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />

              {/* Authenticated routes */}
              <Route
                path="cart"
                element={
                  <RouteGuard>
                    <CartPage />
                  </RouteGuard>
                }
              />
              <Route
                path="dashboard"
                element={
                  <RouteGuard>
                    <DashboardPage />
                  </RouteGuard>
                }
              />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
