"use client";

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

export default function UploadsPage() {
  const [brandId, setBrandId] = useState("1");
  const [file, setFile] = useState<File | null>(null);
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError("Please select a CSV or XLSX file.");
      return;
    }

    setLoading(true);
    setError(null);
    setSummary(null);

    try {
      const formData = new FormData();
      formData.append("brand_id", brandId);
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/imports/sku-master`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const data: ImportSummary = await response.json();
      setSummary(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-10">
      <h1 className="text-3xl font-semibold">SKU Master Upload</h1>

      <form onSubmit={onSubmit} className="space-y-4 rounded border border-slate-200 p-4">
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Brand ID</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            value={brandId}
            onChange={(e) => setBrandId(e.target.value)}
            required
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium">File (CSV/XLSX)</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2"
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
        </label>

        <button disabled={loading} className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60" type="submit">
          {loading ? "Uploading..." : "Upload SKU Master"}
        </button>
      </form>

      {error && <p className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p>}

      {summary && (
        <section className="space-y-3 rounded border border-slate-200 p-4">
          <h2 className="text-xl font-semibold">Import Summary</h2>
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
      )}
    </main>
  );
}
