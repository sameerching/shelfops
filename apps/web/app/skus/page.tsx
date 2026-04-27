"use client";

import { FormEvent, useState } from "react";

type SKU = {
  id: number;
  brand_id: number;
  sku_code: string;
  sku_name: string;
  category: string;
  selling_price: string;
  contribution_margin: string;
  case_pack: string;
  brand: string | null;
  mrp: string | null;
  is_hero_sku: boolean;
  active_flag: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function SkusPage() {
  const [brandId, setBrandId] = useState("1");
  const [rows, setRows] = useState<SKU[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onFetch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/skus?brand_id=${encodeURIComponent(brandId)}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch SKUs (${response.status})`);
      }
      const data: SKU[] = await response.json();
      setRows(data);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch SKUs");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-10">
      <h1 className="text-3xl font-semibold">SKUs</h1>
      <form className="flex items-end gap-3" onSubmit={onFetch}>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Brand ID</span>
          <input
            className="rounded border border-slate-300 px-3 py-2"
            value={brandId}
            onChange={(e) => setBrandId(e.target.value)}
            required
          />
        </label>
        <button className="rounded bg-slate-900 px-4 py-2 text-white" type="submit">
          Load SKUs
        </button>
      </form>

      {error && <p className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p>}

      <div className="overflow-x-auto">
        <table className="min-w-full border border-slate-200 text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-3 py-2 text-left">SKU Code</th>
              <th className="px-3 py-2 text-left">SKU Name</th>
              <th className="px-3 py-2 text-left">Category</th>
              <th className="px-3 py-2 text-left">Selling Price</th>
              <th className="px-3 py-2 text-left">Contribution Margin</th>
              <th className="px-3 py-2 text-left">Case Pack</th>
              <th className="px-3 py-2 text-left">Hero</th>
              <th className="px-3 py-2 text-left">Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((sku) => (
              <tr key={sku.id} className="border-t border-slate-200">
                <td className="px-3 py-2">{sku.sku_code}</td>
                <td className="px-3 py-2">{sku.sku_name}</td>
                <td className="px-3 py-2">{sku.category}</td>
                <td className="px-3 py-2">{sku.selling_price}</td>
                <td className="px-3 py-2">{sku.contribution_margin}</td>
                <td className="px-3 py-2">{sku.case_pack}</td>
                <td className="px-3 py-2">{sku.is_hero_sku ? "Yes" : "No"}</td>
                <td className="px-3 py-2">{sku.active_flag ? "Yes" : "No"}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-slate-500" colSpan={8}>
                  No SKUs loaded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
