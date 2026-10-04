"use client";

import { startTransition, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/** Route error state (DESIGN.md section 14), same markup as components/LoadError. Never shows the error. */
export default function RouteError({ error, reset }: ErrorProps) {
  const router = useRouter();

  useEffect(() => {
    // Server-side details stay in the server log; the digest links this view to that entry.
    console.error("Dashboard failed to load", error.digest ?? error.message);
  }, [error]);

  // Re-fetch the server components, then clear the boundary so the page renders again.
  const retry = () =>
    startTransition(() => {
      router.refresh();
      reset();
    });

  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center text-center p-6">
      <AlertCircle size={48} className="text-red-300 mb-4" />
      <h1 className="text-lg font-semibold text-gray-700">Something went wrong</h1>
      <p className="text-sm text-gray-500 mt-1">Could not load the dashboard data. Please try refreshing.</p>
      <div className="mt-4">
        <button
          type="button"
          onClick={retry}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    </div>
  );
}
