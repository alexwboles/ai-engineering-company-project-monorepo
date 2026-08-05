"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { inventoryApi, type Product } from "@/lib/inventory";
import {
  ErrorState,
  InventoryHeader,
  InventoryNavLink,
  LoadingState,
  LOW_STOCK_THRESHOLD,
} from "@/app/inventory/components/inventory-common";

function getErrorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Unable to load products. Please try again.";
}

function stockTone(stock: number) {
  if (stock <= 0) {
    return {
      label: "Out of stock",
      className: "bg-rose-100 text-rose-800",
      dotClassName: "bg-rose-500",
    };
  }
  if (stock <= LOW_STOCK_THRESHOLD) {
    return {
      label: "Low stock",
      className: "bg-amber-100 text-amber-800",
      dotClassName: "bg-amber-500",
    };
  }
  return {
    label: "Healthy stock",
    className: "bg-emerald-100 text-emerald-800",
    dotClassName: "bg-emerald-500",
  };
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProducts(await inventoryApi.listProducts());
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadProducts(), 0);
    return () => window.clearTimeout(timer);
  }, [loadProducts]);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <InventoryHeader
        eyebrow="Inventory / Products"
        title="Stock overview"
        description="Review current stock for HealthCore inventory and move directly into an inbound or outbound order. Stock is derived from the order history."
      >
        <InventoryNavLink href="/inventory/orders/inbound">Register delivery</InventoryNavLink>
        <InventoryNavLink href="/inventory/orders/outbound">Log consumption</InventoryNavLink>
        <InventoryNavLink href="/inventory/orders">Order history</InventoryNavLink>
      </InventoryHeader>

      {loading ? <LoadingState label="Loading products and current stock..." /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={() => void loadProducts()} /> : null}
      {!loading && !error ? (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-2 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Products</h2>
              <p className="text-sm text-slate-500">{products.length} product{products.length === 1 ? "" : "s"} available</p>
            </div>
            <p className="text-xs text-slate-500">Low stock is {LOW_STOCK_THRESHOLD} units or fewer.</p>
          </div>

          {products.length === 0 ? (
            <p className="p-6 text-sm text-slate-600">No products are available yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Product</th>
                    <th className="px-5 py-3 font-semibold">SKU</th>
                    <th className="px-5 py-3 font-semibold">Current stock</th>
                    <th className="px-5 py-3 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {products.map((product) => {
                    const tone = stockTone(product.current_stock);
                    return (
                      <tr key={product.id} className="text-slate-700">
                        <td className="px-5 py-4 font-medium text-slate-900">{product.name}</td>
                        <td className="px-5 py-4 font-mono text-xs">{product.sku}</td>
                        <td className="px-5 py-4">
                          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${tone.className}`}>
                            <span className={`h-2 w-2 rounded-full ${tone.dotClassName}`} aria-hidden="true" />
                            {product.current_stock} units · {tone.label}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex flex-wrap gap-2">
                            <Link
                              href={`/inventory/orders/inbound?productId=${product.id}`}
                              className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-800"
                            >
                              Inbound order
                            </Link>
                            <Link
                              href={`/inventory/orders/outbound?productId=${product.id}`}
                              className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:border-emerald-400 hover:text-emerald-800"
                            >
                              Outbound order
                            </Link>
                          </div>
                        </td>
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
