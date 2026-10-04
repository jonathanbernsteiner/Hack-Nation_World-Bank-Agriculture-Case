"use client";

import { RefreshCw } from "lucide-react";

export default function RetryButton() {
  return (
    <button
      type="button"
      onClick={() => window.location.reload()}
      className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors"
    >
      <RefreshCw size={14} /> Retry
    </button>
  );
}
