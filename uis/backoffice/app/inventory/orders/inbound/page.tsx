"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { inventoryApi, type Product } from "@/lib/inventory";
import {
  ErrorState,
  InventoryHeader,
  InventoryNavLink,
  LoadingState,
} from "@/app/inventory/components/inventory-common";

function getErrorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Unable to complete the request. Please try again.";
}

function parsePositiveInteger(value: string) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export default function InboundOrderPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadProducts = useCallback(async () => {
    setLoadingProducts(true);
    setLoadError(null);
    try {
      const loadedProducts = await inventoryApi.listProducts();
      setProducts(loadedProducts);
      const requestedProductId = new URLSearchParams(window.location.search).get("productId");
      if (requestedProductId && loadedProducts.some((product) => String(product.id) === requestedProductId)) {
        setProductId(requestedProductId);
      }
    } catch (requestError) {
      setLoadError(getErrorMessage(requestError));
    } finally {
      setLoadingProducts(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadProducts(), 0);
    return () => window.clearTimeout(timer);
  }, [loadProducts]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);

    const parsedProductId = parsePositiveInteger(productId);
    const parsedQuantity = parsePositiveInteger(quantity);
    if (!parsedProductId || !parsedQuantity) {
      setFormError("Choose a product and enter a whole quantity greater than zero.");
      return;
    }

    setSubmitting(true);
    try {
      await inventoryApi.createInboundOrder({ product_id: parsedProductId, quantity: parsedQuantity });
      setProductId("");
      setQuantity("");
      setSuccessMessage("Inbound order registered successfully. Current stock will update after the next refresh.");
    } catch (requestError) {
      setFormError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <InventoryHeader
        eyebrow="Inventory / Inbound order"
        title="Register a delivery"
        description="Record stock received by HealthCore. The product selector uses the available product catalogue, so operators never need to enter a raw product ID."
      >
        <InventoryNavLink href="/inventory/products">Products</InventoryNavLink>
        <InventoryNavLink href="/inventory/orders/outbound">Log consumption</InventoryNavLink>
        <InventoryNavLink href="/inventory/orders">Order history</InventoryNavLink>
      </InventoryHeader>

      {loadingProducts ? <LoadingState label="Loading products for the delivery form..." /> : null}
      {!loadingProducts && loadError ? <ErrorState message={loadError} onRetry={() => void loadProducts()} /> : null}
      {!loadingProducts && !loadError ? (
        <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="grid gap-5">
            <div>
              <label htmlFor="inbound-product" className="text-sm font-semibold text-slate-800">Product</label>
              <select
                id="inbound-product"
                value={productId}
                onChange={(event) => setProductId(event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              >
                <option value="">Select a product</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>{product.name} ({product.sku})</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="inbound-quantity" className="text-sm font-semibold text-slate-800">Quantity received</label>
              <input
                id="inbound-quantity"
                type="number"
                min="1"
                step="1"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
                placeholder="e.g. 25"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              />
            </div>

            {formError ? <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{formError}</p> : null}
            {successMessage ? <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{successMessage}</p> : null}

            <button
              type="submit"
              disabled={submitting || products.length === 0}
              className="rounded-lg bg-emerald-700 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {submitting ? "Registering delivery..." : "Register inbound order"}
            </button>
          </div>
        </form>
      ) : null}
    </main>
  );
}
