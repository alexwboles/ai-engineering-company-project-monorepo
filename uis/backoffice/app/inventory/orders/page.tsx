"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { inventoryApi, type InventoryOrder } from "@/lib/inventory";
import {
  ErrorState,
  formatDate,
  InventoryHeader,
  InventoryNavLink,
  LoadingState,
} from "@/app/inventory/components/inventory-common";

function getErrorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Unable to load order history. Please try again.";
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<InventoryOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setOrders(await inventoryApi.listOrders());
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadOrders(), 0);
    return () => window.clearTimeout(timer);
  }, [loadOrders]);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <InventoryHeader
        eyebrow="Inventory / Order history"
        title="Order history"
        description="Review the immutable inbound and outbound order record, including the product, quantity, creation date, and HealthCore user UUID that created each order."
      >
        <InventoryNavLink href="/inventory/products">Products</InventoryNavLink>
        <InventoryNavLink href="/inventory/orders/inbound">Register delivery</InventoryNavLink>
        <InventoryNavLink href="/inventory/orders/outbound">Log consumption</InventoryNavLink>
      </InventoryHeader>

      {loading ? <LoadingState label="Loading inbound and outbound orders..." /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={() => void loadOrders()} /> : null}
      {!loading && !error ? (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-lg font-semibold text-slate-900">Recorded orders</h2>
            <p className="text-sm text-slate-500">{orders.length} order{orders.length === 1 ? "" : "s"} in the history</p>
          </div>

          {orders.length === 0 ? (
            <p className="p-6 text-sm text-slate-600">No inbound or outbound orders have been recorded.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Type</th>
                    <th className="px-5 py-3 font-semibold">Product</th>
                    <th className="px-5 py-3 font-semibold">Quantity</th>
                    <th className="px-5 py-3 font-semibold">Created</th>
                    <th className="px-5 py-3 font-semibold">Created by user UUID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {orders.map((order) => {
                    const isInbound = order.order_type === "inbound";
                    return (
                      <tr key={`${order.order_type}-${order.id}`} className="text-slate-700">
                        <td className="px-5 py-4">
                          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${isInbound ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                            {isInbound ? "Inbound" : "Outbound"}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <p className="font-medium text-slate-900">{order.product.name}</p>
                          <p className="font-mono text-xs text-slate-500">{order.product.sku}</p>
                        </td>
                        <td className="px-5 py-4 font-semibold">{order.quantity} units</td>
                        <td className="whitespace-nowrap px-5 py-4">{formatDate(order.created_at)}</td>
                        <td className="px-5 py-4 font-mono text-xs text-slate-500">{order.user_uuid}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}
    </main>
  );
}
