"use client";

import { FormEvent, useState } from "react";

type InventoryRow = {
  id: number;
  sku_code: string;
  sku_name: string;
  warehouse: string;
  city: string;
  available_qty: string;
  timestamp: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

export default function InventoryPage() {
  const [brandId, setBrandId] = useState("1");
  const [skuCode, setSkuCode] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [city, setCity] = useState("");
  const [rows, setRows] = useState<InventoryRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onFetch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      const params = new URLSearchParams({ brand_id: brandId });
      if (skuCode) params.append("sku_code", skuCode);
      if (warehouse) params.append("warehouse", warehouse);
      if (city) params.append("city", city);

      const response = await fetch(`${API_BASE}/inventory?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch inventory (${response.status})`);
      }
      const data: InventoryRow[] = await response.json();
      setRows(data);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch inventory");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-10">
      <h1 className="text-3xl font-semibold">Inventory Positions</h1>

      <form className="grid gap-3 rounded border border-slate-200 p-4 md:grid-cols-5" onSubmit={onFetch}>
        <input className="rounded border px-3 py-2" placeholder="Brand ID" value={brandId} onChange={(e) => setBrandId(e.target.value)} required />
        <input className="rounded border px-3 py-2" placeholder="SKU code" value={skuCode} onChange={(e) => setSkuCode(e.target.value)} />
        <input className="rounded border px-3 py-2" placeholder="Warehouse" value={warehouse} onChange={(e) => setWarehouse(e.target.value)} />
        <input className="rounded border px-3 py-2" placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
        <button className="rounded bg-slate-900 px-4 py-2 text-white" type="submit">
          Load
        </button>
      </form>

      {error && <p className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p>}

      <div className="overflow-x-auto">
        <table className="min-w-full border border-slate-200 text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-3 py-2 text-left">Timestamp</th>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Warehouse</th>
              <th className="px-3 py-2 text-left">City</th>
              <th className="px-3 py-2 text-left">Available Qty</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-200">
                <td className="px-3 py-2">{new Date(row.timestamp).toLocaleString()}</td>
                <td className="px-3 py-2">{row.sku_code} — {row.sku_name}</td>
                <td className="px-3 py-2">{row.warehouse}</td>
                <td className="px-3 py-2">{row.city}</td>
                <td className="px-3 py-2">{row.available_qty}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-slate-500" colSpan={5}>
                  No inventory rows loaded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
