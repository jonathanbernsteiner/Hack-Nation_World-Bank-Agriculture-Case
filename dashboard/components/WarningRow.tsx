import Link from "next/link";
import { AlertTriangle, TrendingDown } from "lucide-react";
import type { Warning } from "@/lib/types";

const PILL = "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]";

interface WarningRowProps {
  warning: Warning;
  showMapLink?: boolean;
  href?: string;
}

export default function WarningRow({ warning, showMapLink = false, href }: WarningRowProps) {
  const isProblem = warning.kind === "problem";
  const Icon = isProblem ? AlertTriangle : TrendingDown;
  const content = (
    <>
      <Icon size={20} className={`shrink-0 ${isProblem ? "text-red-600" : "text-amber-500"}`} />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-ink">{warning.title}</div>
        <div className="text-sm text-muted">{warning.detail}</div>
      </div>
      <span className={`${PILL} shrink-0 whitespace-nowrap`}>Officer check</span>
    </>
  );
  const ROW = "flex items-center gap-4 px-6 py-4";
  return (
    <li className="border-b border-gray-100 last:border-b-0 hover:bg-slate-50 transition-colors">
      {href ? (
        <Link href={href} className={`${ROW} focus-visible:outline-2 focus-visible:outline-accent`}>
          {content}
        </Link>
      ) : (
        <div className={ROW}>
          {content}
          {showMapLink && (
            <Link
              href={`/map?path=${encodeURIComponent(warning.path.join("|"))}`}
              className="shrink-0 text-xs font-medium text-accent hover:underline whitespace-nowrap"
            >
              View on map
            </Link>
          )}
        </div>
      )}
    </li>
  );
}
