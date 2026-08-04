import { apiRequest } from "@/lib/api-client";

const INVENTORY_API_URL =
  process.env.NEXT_PUBLIC_INVENTORY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

export type OrderType = "inbound" | "outbound";

export interface Product {
  id: number;
  name: string;
  sku: string;
  current_stock: number;
}

export interface InventoryOrder {
  id: number;
  product_id: number;
  quantity: number;
  created_at: string;
  user_uuid: string;
  order_type: OrderType;
  product: {
    id: number;
    name: string;
    sku: string;
  };
}

interface OrderPayload {
  product_id: number;
  quantity: number;
}

function request<T>(path: string, init: RequestInit = {}) {
  return apiRequest<T>(path, init, { baseUrl: INVENTORY_API_URL });
}

export const inventoryApi = {
  listProducts: () => request<Product[]>("/inventory/products"),

  getProduct: (productId: number) => request<Product>(`/inventory/products/${productId}`),

  createInboundOrder: (payload: OrderPayload) =>
    request<InventoryOrder>("/inventory/orders/inbound", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createOutboundOrder: (payload: OrderPayload) =>
    request<InventoryOrder>("/inventory/orders/outbound", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listOrders: () => request<InventoryOrder[]>("/inventory/orders"),
};
