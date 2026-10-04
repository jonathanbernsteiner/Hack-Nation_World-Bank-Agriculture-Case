import {
  MIN_FARMERS,
  MIN_SALES,
  PRICE_LOW_INDEX,
  PRICE_WINDOW_DAYS,
  PROBLEM_BASELINE_WEEKS,
  PROBLEM_MIN_FARMERS,
  PROBLEM_WINDOW_DAYS,
} from "@/lib/types";

const WORKSPACE: [string, string][] = [
  ["Country", "Uganda"],
  ["Hotline language", "Kiswahili"],
  ["Currency", "UGX"],
  ["Time zone", "Africa/Kampala (EAT)"],
  ["Price reference", "UCDA / MAAIF monthly farm-gate"],
];

const RULES: [string, string][] = [
  ["Problem warning", `${PROBLEM_MIN_FARMERS}+ farms in one parish within ${PROBLEM_WINDOW_DAYS} days`],
  ["Problem baseline", `More farms than in the ${PROBLEM_BASELINE_WEEKS} weeks before`],
  ["Price warning", `${Math.round((1 - PRICE_LOW_INDEX) * 100)}%+ below national over ${PRICE_WINDOW_DAYS} days`],
  ["Minimum for a median", `${MIN_SALES} sales from ${MIN_FARMERS} farmers`],
];

function Rows({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="bg-white border border-line rounded-xl divide-y divide-gray-100">
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between gap-4 px-6 py-3 text-sm">
          <dt className="text-muted whitespace-nowrap">{label}</dt>
          <dd className="text-gray-900 text-right">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function SettingsView() {
  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6 max-w-3xl">
      <section>
        <h2 className="text-base font-semibold text-ink mb-4">Workspace</h2>
        <Rows rows={WORKSPACE} />
      </section>
      <section>
        <h2 className="text-base font-semibold text-ink mb-4">Warning rules</h2>
        <Rows rows={RULES} />
      </section>
    </div>
  );
}
