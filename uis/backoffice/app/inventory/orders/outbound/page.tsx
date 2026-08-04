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

export default function OutboundOrderPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [quantity, setQuantity] = useState("");
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [loadingStock, setLoadingStock] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [stockError, setStockError] = useState<string | null>(null);
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
        setSelectedProductId(requestedProductId);
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

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      if (!selectedProductId) {
        setSelectedProduct(null);
        setStockError(null);
        setLoadingStock(false);
        return;
      }

      setLoadingStock(true);
      setStockError(null);
      setSelectedProduct(null);
      void inventoryApi
        .getProduct(Number(selectedProductId))
        .then((product) => {
          if (active) {
            setSelectedProduct(product);
          }
        })
        .catch((requestError: unknown) => {
          if (active) {
            setStockError(getErrorMessage(requestError));
          }
        })
        .finally(() => {
          if (active) {
            setLoadingStock(false);
          }
        });
    }, 0);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [selectedProductId]);

  const parsedQuantity = parsePositiveInteger(quantity);
  const availableStock = selectedProduct?.current_stock ?? null;
  const exceedsStock = availableStock !== null && parsedQuantity !== null && parsedQuantity > availableStock;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);

    const productId = parsePositiveInteger(selectedProductId);
    if (!productId || !parsedQuantity) {
      setFormError("Choose a product and enter a whole quantity greater than zero.");
      return;
    }
    if (loadingStock || availableStock === null) {
      setFormError("Wait for the selected product's current stock to load before submitting.");
      return;
    }
    if (exceedsStock) {
      setFormError(`Quantity exceeds available stock. Only ${availableStock} units are available.`);
      return;
    }

    setSubmitting(true);
    try {
      await inventoryApi.createOutboundOrder({ product_id: productId, quantity: parsedQuantity });
      setSelectedProductId("");
      setQuantity("");
      setSuccessMessage("Outbound order registered successfully.");
    } catch (requestError) {
      setFormError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-8">
      <InventoryHeader
        eyebrow="Inventory / Outbound order"
        title="Log consumption or exit"
        description="Select a product to see its live available stock before recording an outbound order. The API remains the final protection against insufficient stock."
      >
        <InventoryNavLink href="/inventory/products">Products</InventoryNavLink>
        <InventoryNavLink href="/inventory/orders/inbound">Register delivery</InventoryNavLink>
        <InventoryNavLink href="/inventory/orders">Order history</InventoryNavLink>
      </InventoryHeader>

      {loadingProducts ? <LoadingState label="Loading products for the consumption form..." /> : null}
      {!loadingProducts && loadError ? <ErrorState message={loadError} onRetry={() => void loadProducts()} /> : null}
      {!loadingProducts && !loadError ? (
        <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="grid gap-5">
            <div>
              <label htmlFor="outbound-product" className="text-sm font-semibold text-slate-800">Product</label>
              <select
                id="outbound-product"
                value={selectedProductId}
                onChange={(event) => {
                  setSelectedProductId(event.target.value);
                  setFormError(null);
                  setSuccessMessage(null);
                }}
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              >
                <option value="">Select a product</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>{product.name} ({product.sku})</option>
                ))}
              </select>
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-800">Available stock: </span>
              {loadingStock ? <span className="text-slate-500">Checking selected product...</span> : null}
              {!loadingStock && selectedProduct ? <span className="font-semibold text-emerald-700">{selectedProduct.current_stock} units</span> : null}
              {!loadingStock && !selectedProduct && !stockError ? <span className="text-slate-500">Select a product to check stock.</span> : null}
              {stockError ? <span role="alert" className="text-rose-700">{stockError}</span> : null}
            </div>

            <div>
              <label htmlFor="outbound-quantity" className="text-sm font-semibold text-slate-800">Quantity to remove</label>
              <input
                id="outbound-quantity"
                type="number"
                min="1"
                step="1"
                value={quantity}
                onChange={(event) => {
                  setQuantity(event.target.value);
                  setFormError(null);
                }}
                placeholder="e.g. 4"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              />
              {exceedsStock ? (
                <p role="alert" className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  This quantity exceeds the {availableStock}-unit stock currently available. Reduce the quantity before submitting.
                </p>
              ) : null}
              {formError ? <p role="alert" className="mt-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{formError}</p> : null}
            </div>

            {successMessage ? <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{successMessage}</p> : null}

            <button
              type="submit"
              disabled={submitting || products.length === 0 || loadingStock || exceedsStock}
              className="rounded-lg bg-emerald-700 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {submitting ? "Logging consumption..." : "Register outbound order"}
            </button>
          </div>
        </form>
      ) : null}
    </main>
  );
}
