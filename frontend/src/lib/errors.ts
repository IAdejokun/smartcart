import axios from "axios";

/**
 * Extracts a user-facing error message from a thrown error.
 *
 * Priority:
 * 1. FastAPI/Pydantic returns { detail: "..." } in response body — use that
 * 2. Axios native error message (network errors, timeouts)
 * 3. Generic Error.message (anything else)
 * 4. Fallback string
 *
 * Using `unknown` instead of `any` keeps strict TypeScript happy and forces
 * callers to narrow the error type explicitly.
 */
export function getErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (err.message) return err.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}
