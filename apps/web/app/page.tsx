import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center gap-4 px-6 py-12">
      <h1 className="text-4xl font-semibold tracking-tight">ShelfOps</h1>
      <p className="text-lg text-slate-700">Phase 1 SKU Master upload workflow.</p>
      <div className="flex gap-3">
        <Link className="rounded bg-slate-900 px-4 py-2 text-white" href="/uploads">
          Uploads
        </Link>
        <Link className="rounded border border-slate-300 px-4 py-2" href="/skus">
          SKUs
        </Link>
      </div>
    </main>
  );
}
