import { AlertCircle } from "lucide-react";
import RetryButton from "./RetryButton";

/** Route error state (DESIGN.md section 14). Never shows the underlying error. */
export default function LoadError() {
  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center text-center p-6">
      <AlertCircle size={48} className="text-red-300 mb-4" />
      <h1 className="text-lg font-semibold text-gray-700">Something went wrong</h1>
      <p className="text-sm text-gray-500 mt-1">Could not load the dashboard data. Please try refreshing.</p>
      <div className="mt-4">
        <RetryButton />
      </div>
    </div>
  );
}
