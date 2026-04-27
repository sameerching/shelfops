"use client";

import { FormEvent, useState } from "react";

type SalesVelocityRow = {
  id: number;
  sku_code: string;
  sku_name: string;
  platform: string;
  city: string;
  avg_units_per_day: string;
  updated_at: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

export default function SalesVelocityPage() {
  const [brandId, setBrandId] = useState("1");
  const [skuCode, setSkuCode] = useState("");
  const [platform, setPlatform] = useState("");
  const [city, setCity] = useState("");
  const [rows, setRows] = useState<SalesVelocityRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onFetch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      const params = new URLSearchParams({ brand_id: brandId });
      if (skuCode) params.append("sku_code", skuCode);
      if (platform) params.append("platform", platform);
      if (city) params.append("city", city);

      const response = await fetch(`${API_BASE}/sales-velocity?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch sales velocity (${response.status})`);
      }
      const data: SalesVelocityRow[] = await response.json();
      setRows(data);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch sales velocity");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-10">
      <h1 className="text-3xl font-semibold">Sales Velocity</h1>

      <form className="grid gap-3 rounded border border-slate-200 p-4 md:grid-cols-5" onSubmit={onFetch}>
        <input className="rounded border px-3 py-2" placeholder="Brand ID" value={brandId} onChange={(e) => setBrandId(e.target.value)} required />
        <input className="rounded border px-3 py-2" placeholder="SKU code" value={skuCode} onChange={(e) => setSkuCode(e.target.value)} />
        <input className="rounded border px-3 py-2" placeholder="Platform" value={platform} onChange={(e) => setPlatform(e.target.value)} />
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
              <th className="px-3 py-2 text-left">Updated</th>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Platform</th>
              <th className="px-3 py-2 text-left">City</th>
              <th className="px-3 py-2 text-left">Avg Units / Day</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-200">
                <td className="px-3 py-2">{new Date(row.updated_at).toLocaleString()}</td>
                <td className="px-3 py-2">{row.sku_code} — {row.sku_name}</td>
                <td className="px-3 py-2">{row.platform}</td>
                <td className="px-3 py-2">{row.city}</td>
                <td className="px-3 py-2">{row.avg_units_per_day}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-slate-500" colSpan={5}>
                  No sales velocity rows loaded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
