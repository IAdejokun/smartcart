import { apiClient } from "./client";
import type { TokenResponse, UserResponse } from "../types/api";

export async function register(
  email: string,
  password: string,
): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>("/auth/register", {
    email,
    password,
  });
  return response.data;
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/auth/login", {
    email,
    password,
  });
  return response.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>("/auth/me");
  return response.data;
}
