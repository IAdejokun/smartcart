import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "../store/authStore";

// API base URL — Vite injects this from .env at build time
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// --- Request interceptor: attach access token ---
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Response interceptor: transparent token refresh on 401 ---
//
// The pattern: when a request returns 401, we attempt one refresh using the
// refresh token. If refresh succeeds, we retry the original request. If refresh
// fails, we clear auth state and propagate the 401 — the route guard will
// redirect to /login.
//
// The `_retry` flag prevents infinite loops if /auth/refresh itself returns 401.
//
// CONCURRENCY: if N requests arrive simultaneously and all 401, naive code would
// trigger N refresh requests. We solve this with a single-flight refresh promise
// — all requests wait on the same in-flight refresh, then retry with the new token.

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = useAuthStore.getState().refreshToken;
  if (!refreshToken) return null;

  try {
    const response = await axios.post(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { "Content-Type": "application/json" } },
    );
    const { access_token, refresh_token: newRefreshToken } = response.data;
    useAuthStore.getState().setTokens(access_token, newRefreshToken);
    return access_token;
  } catch {
    useAuthStore.getState().clearAuth();
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Single-flight: all concurrent 401s wait on the same refresh
      refreshPromise = refreshPromise || refreshAccessToken();
      const newToken = await refreshPromise;
      refreshPromise = null;

      if (newToken && originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      }
    }

    return Promise.reject(error);
  },
);
