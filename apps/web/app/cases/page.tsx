"use client";

import { FormEvent, useState } from "react";

type CaseRow = {
  id: number;
  sku_code: string;
  sku_name: string;
  platform: string;
  city: string;
  location: string;
  status: string;
  priority: string;
  stockout_duration_hours: string;
  estimated_lost_sales: string;
  estimated_lost_margin: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

export default function CasesPage() {
  const [brandId, setBrandId] = useState("1");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [platform, setPlatform] = useState("");
  const [city, setCity] = useState("");
  const [rows, setRows] = useState<CaseRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadCases = async () => {
    const params = new URLSearchParams({ brand_id: brandId });
    if (status) params.append("status", status);
    if (priority) params.append("priority", priority);
    if (platform) params.append("platform", platform);
    if (city) params.append("city", city);

    const response = await fetch(`${API_BASE}/cases?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch cases (${response.status})`);
    }

    const data: CaseRow[] = await response.json();
    setRows(data);
  };

  const onFetch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setMessage(null);

    try {
      await loadCases();
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to fetch cases");
    }
  };

  const onGenerate = async () => {
    setError(null);
    setMessage(null);

    try {
      const response = await fetch(`${API_BASE}/cases/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand_id: Number(brandId) }),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate cases (${response.status})`);
      }

      const payload = await response.json();
      setMessage(
        `Generated: ${payload.generated_cases}, updated: ${payload.updated_cases}, recovered: ${payload.recovered_cases}`,
      );
      await loadCases();
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "Failed to generate cases");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-6 py-10">
      <h1 className="text-3xl font-semibold">Stockout Cases</h1>

      <div className="flex flex-wrap items-center gap-3">
        <input
          className="rounded border px-3 py-2"
          placeholder="Brand ID"
          value={brandId}
          onChange={(e) => setBrandId(e.target.value)}
          required
        />
        <button className="rounded bg-emerald-600 px-4 py-2 text-white" type="button" onClick={onGenerate}>
          Generate Cases
        </button>
      </div>

      <form className="grid gap-3 rounded border border-slate-200 p-4 md:grid-cols-6" onSubmit={onFetch}>
        <input className="rounded border px-3 py-2" placeholder="Brand ID" value={brandId} onChange={(e) => setBrandId(e.target.value)} required />
        <input className="rounded border px-3 py-2" placeholder="Status" value={status} onChange={(e) => setStatus(e.target.value)} />
        <input className="rounded border px-3 py-2" placeholder="Priority" value={priority} onChange={(e) => setPriority(e.target.value)} />
        <input className="rounded border px-3 py-2" placeholder="Platform" value={platform} onChange={(e) => setPlatform(e.target.value)} />
        <input className="rounded border px-3 py-2" placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
        <button className="rounded bg-slate-900 px-4 py-2 text-white" type="submit">
          Load
        </button>
      </form>

      {message && <p className="rounded border border-emerald-200 bg-emerald-50 p-3 text-emerald-700">{message}</p>}
      {error && <p className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p>}

      <div className="overflow-x-auto">
        <table className="min-w-full border border-slate-200 text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Platform</th>
              <th className="px-3 py-2 text-left">City</th>
              <th className="px-3 py-2 text-left">Location</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Priority</th>
              <th className="px-3 py-2 text-left">Duration (hours)</th>
              <th className="px-3 py-2 text-left">Estimated Lost Sales</th>
              <th className="px-3 py-2 text-left">Estimated Lost Margin</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-200">
                <td className="px-3 py-2">{row.sku_code} — {row.sku_name}</td>
                <td className="px-3 py-2">{row.platform}</td>
                <td className="px-3 py-2">{row.city}</td>
                <td className="px-3 py-2">{row.location}</td>
                <td className="px-3 py-2">{row.status}</td>
                <td className="px-3 py-2">{row.priority}</td>
                <td className="px-3 py-2">{row.stockout_duration_hours}</td>
                <td className="px-3 py-2">{row.estimated_lost_sales}</td>
                <td className="px-3 py-2">{row.estimated_lost_margin}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-slate-500" colSpan={9}>
                  No cases loaded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
