import { apiClient } from "./client";
import type { ProductDetail, ProductListResponse } from "../types/api";

export interface ListProductsParams {
  category?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export async function listProducts(
  params: ListProductsParams = {},
): Promise<ProductListResponse> {
  const response = await apiClient.get<ProductListResponse>("/products", {
    params,
  });
  return response.data;
}

export async function getProduct(productId: string): Promise<ProductDetail> {
  const response = await apiClient.get<ProductDetail>(`/products/${productId}`);
  return response.data;
}

export async function listCategories(): Promise<string[]> {
  const response = await apiClient.get<string[]>("/products/categories");
  return response.data;
}
