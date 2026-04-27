"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

type RowError = {
  row_number: number;
  column_name: string;
  error_code: string;
  error_message: string;
};

type ImportSummary = {
  import_batch_id: number;
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  duplicate_rows: number;
  errors: RowError[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

function SummaryCard({ title, summary }: { title: string; summary: ImportSummary | null }) {
  if (!summary) {
    return null;
  }

  return (
    <section className="space-y-3 rounded border border-slate-200 p-4">
      <h2 className="text-xl font-semibold">{title} Summary</h2>
      <ul className="grid grid-cols-2 gap-2 text-sm">
        <li>Batch ID: {summary.import_batch_id}</li>
        <li>Total Rows: {summary.total_rows}</li>
        <li>Accepted Rows: {summary.accepted_rows}</li>
        <li>Rejected Rows: {summary.rejected_rows}</li>
        <li>Duplicate Rows: {summary.duplicate_rows}</li>
      </ul>

      {summary.errors.length > 0 && (
        <div>
          <h3 className="mb-2 text-lg font-medium">Row Errors</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full border border-slate-200 text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-3 py-2 text-left">Row</th>
                  <th className="px-3 py-2 text-left">Column</th>
                  <th className="px-3 py-2 text-left">Code</th>
                  <th className="px-3 py-2 text-left">Message</th>
                </tr>
              </thead>
              <tbody>
                {summary.errors.map((rowError, idx) => (
                  <tr key={`${rowError.row_number}-${rowError.column_name}-${idx}`} className="border-t border-slate-200">
                    <td className="px-3 py-2">{rowError.row_number}</td>
                    <td className="px-3 py-2">{rowError.column_name}</td>
                    <td className="px-3 py-2">{rowError.error_code}</td>
                    <td className="px-3 py-2">{rowError.error_message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

export default function UploadsPage() {
  const [brandId, setBrandId] = useState("1");
  const [skuFile, setSkuFile] = useState<File | null>(null);
  const [availabilityFile, setAvailabilityFile] = useState<File | null>(null);
  const [salesVelocityFile, setSalesVelocityFile] = useState<File | null>(null);
  const [inventoryFile, setInventoryFile] = useState<File | null>(null);
  const [poFile, setPoFile] = useState<File | null>(null);
  const [dispatchFile, setDispatchFile] = useState<File | null>(null);
  const [grnFile, setGrnFile] = useState<File | null>(null);
  const [skuSummary, setSkuSummary] = useState<ImportSummary | null>(null);
  const [availabilitySummary, setAvailabilitySummary] = useState<ImportSummary | null>(null);
  const [salesVelocitySummary, setSalesVelocitySummary] = useState<ImportSummary | null>(null);
  const [inventorySummary, setInventorySummary] = useState<ImportSummary | null>(null);
  const [poSummary, setPoSummary] = useState<ImportSummary | null>(null);
  const [dispatchSummary, setDispatchSummary] = useState<ImportSummary | null>(null);
  const [grnSummary, setGrnSummary] = useState<ImportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingSku, setLoadingSku] = useState(false);
  const [loadingAvailability, setLoadingAvailability] = useState(false);
  const [loadingSalesVelocity, setLoadingSalesVelocity] = useState(false);
  const [loadingInventory, setLoadingInventory] = useState(false);
  const [loadingPo, setLoadingPo] = useState(false);
  const [loadingDispatch, setLoadingDispatch] = useState(false);
  const [loadingGrn, setLoadingGrn] = useState(false);

  const upload = async (endpoint: string, file: File): Promise<ImportSummary> => {
    const formData = new FormData();
    formData.append("brand_id", brandId);
    formData.append("file", file);

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }

    return response.json();
  };

  const onSkuSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!skuFile) {
      setError("Please select a SKU Master CSV/XLSX file.");
      return;
    }
    setError(null);
    setLoadingSku(true);
    try {
      const data = await upload("/imports/sku-master", skuFile);
      setSkuSummary(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setLoadingSku(false);
    }
  };

  const onAvailabilitySubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!availabilityFile) {
      setError("Please select an Availability CSV/XLSX file.");
      return;
    }
    setError(null);
    setLoadingAvailability(true);
    try {
      const data = await upload("/imports/availability", availabilityFile);
      setAvailabilitySummary(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setLoadingAvailability(false);
    }
  };

  const onSalesVelocitySubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!salesVelocityFile) {
      setError("Please select a Sales Velocity CSV/XLSX file.");
      return;
    }
    setError(null);
    setLoadingSalesVelocity(true);
    try {
      const data = await upload("/imports/sales-velocity", salesVelocityFile);
      setSalesVelocitySummary(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setLoadingSalesVelocity(false);
    }
  };

  const onInventorySubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inventoryFile) {
      setError("Please select an Inventory CSV/XLSX file.");
      return;
    }
    setError(null);
    setLoadingInventory(true);
    try {
      const data = await upload("/imports/inventory", inventoryFile);
      setInventorySummary(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setLoadingInventory(false);
    }
  };

  const onPoSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!poFile) {
      setError("Please select a PO Tracker CSV/XLSX file.");
      return;
    }
    setError(null);
    setLoadingPo(true);
    try {
      const data = await upload("/imports/po", poFile);
      setPoSummary(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setLoadingPo(false);
    }
  };

  const onDispatchSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!dispatchFile) {
      setError("Please select a Dispatch Tracker CSV/XLSX file.");
      return;
    }
    setError(null);
    setLoadingDispatch(true);
    try {
      const data = await upload("/imports/dispatch", dispatchFile);
      setDispatchSummary(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setLoadingDispatch(false);
    }
  };

  const onGrnSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!grnFile) {
      setError("Please select a GRN Tracker CSV/XLSX file.");
      return;
    }
    setError(null);
    setLoadingGrn(true);
    try {
      const data = await upload("/imports/grn", grnFile);
      setGrnSummary(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setLoadingGrn(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-10">
      <h1 className="text-3xl font-semibold">Uploads</h1>
      <p className="text-sm text-slate-600">
        Upload SKU master, availability, sales velocity, inventory, PO, dispatch, and GRN reports. View imported availability snapshots on the{" "}
        <Link className="underline" href="/availability">
          Availability page
        </Link>
        {" "}and sales velocity rows on the{" "}
        <Link className="underline" href="/sales-velocity">
          Sales Velocity page
        </Link>
        {" "}and inventory rows on the{" "}
        <Link className="underline" href="/inventory">
          Inventory page
        </Link>
        {" "}, PO rows on the{" "}
        <Link className="underline" href="/po-records">
          PO Records page
        </Link>
        {" "}, dispatch rows on the{" "}
        <Link className="underline" href="/dispatch-records">
          Dispatch Records page
        </Link>
        {" "}and GRN rows on the{" "}
        <Link className="underline" href="/grn-records">
          GRN Records page
        </Link>
        .
      </p>

      <label className="block max-w-xs">
        <span className="mb-1 block text-sm font-medium">Brand ID</span>
        <input
          className="w-full rounded border border-slate-300 px-3 py-2"
          value={brandId}
          onChange={(e) => setBrandId(e.target.value)}
          required
        />
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <form onSubmit={onSkuSubmit} className="space-y-4 rounded border border-slate-200 p-4">
          <h2 className="text-lg font-semibold">SKU Master Upload</h2>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setSkuFile(e.target.files?.[0] ?? null)}
            required
          />
          <button disabled={loadingSku} className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60" type="submit">
            {loadingSku ? "Uploading..." : "Upload SKU Master"}
          </button>
        </form>

        <form onSubmit={onAvailabilitySubmit} className="space-y-4 rounded border border-slate-200 p-4">
          <h2 className="text-lg font-semibold">Availability Report Upload</h2>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setAvailabilityFile(e.target.files?.[0] ?? null)}
            required
          />
          <button
            disabled={loadingAvailability}
            className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
            type="submit"
          >
            {loadingAvailability ? "Uploading..." : "Upload Availability"}
          </button>
        </form>

        <form onSubmit={onSalesVelocitySubmit} className="space-y-4 rounded border border-slate-200 p-4">
          <h2 className="text-lg font-semibold">Sales Velocity Upload</h2>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setSalesVelocityFile(e.target.files?.[0] ?? null)}
            required
          />
          <button
            disabled={loadingSalesVelocity}
            className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
            type="submit"
          >
            {loadingSalesVelocity ? "Uploading..." : "Upload Sales Velocity"}
          </button>
        </form>

        <form onSubmit={onInventorySubmit} className="space-y-4 rounded border border-slate-200 p-4">
          <h2 className="text-lg font-semibold">Inventory Report Upload</h2>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setInventoryFile(e.target.files?.[0] ?? null)}
            required
          />
          <button
            disabled={loadingInventory}
            className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
            type="submit"
          >
            {loadingInventory ? "Uploading..." : "Upload Inventory"}
          </button>
        </form>

        <form onSubmit={onPoSubmit} className="space-y-4 rounded border border-slate-200 p-4">
          <h2 className="text-lg font-semibold">PO Tracker Upload</h2>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setPoFile(e.target.files?.[0] ?? null)}
            required
          />
          <button disabled={loadingPo} className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60" type="submit">
            {loadingPo ? "Uploading..." : "Upload PO Tracker"}
          </button>
        </form>

        <form onSubmit={onDispatchSubmit} className="space-y-4 rounded border border-slate-200 p-4">
          <h2 className="text-lg font-semibold">Dispatch Tracker Upload</h2>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setDispatchFile(e.target.files?.[0] ?? null)}
            required
          />
          <button
            disabled={loadingDispatch}
            className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
            type="submit"
          >
            {loadingDispatch ? "Uploading..." : "Upload Dispatch Tracker"}
          </button>
        </form>

        <form onSubmit={onGrnSubmit} className="space-y-4 rounded border border-slate-200 p-4">
          <h2 className="text-lg font-semibold">GRN Tracker Upload</h2>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setGrnFile(e.target.files?.[0] ?? null)}
            required
          />
          <button disabled={loadingGrn} className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60" type="submit">
            {loadingGrn ? "Uploading..." : "Upload GRN Tracker"}
          </button>
        </form>
      </div>

      {error && <p className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p>}

      <SummaryCard title="SKU Master Import" summary={skuSummary} />
      <SummaryCard title="Availability Import" summary={availabilitySummary} />
      <SummaryCard title="Sales Velocity Import" summary={salesVelocitySummary} />
      <SummaryCard title="Inventory Import" summary={inventorySummary} />
      <SummaryCard title="PO Tracker Import" summary={poSummary} />
      <SummaryCard title="Dispatch Tracker Import" summary={dispatchSummary} />
      <SummaryCard title="GRN Tracker Import" summary={grnSummary} />
    </main>
  );
}
