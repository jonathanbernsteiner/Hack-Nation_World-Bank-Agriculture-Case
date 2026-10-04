import {
  PRICE_LOW_INDEX,
  PRICE_WINDOW_DAYS,
  PROBLEM_BASELINE_WEEKS,
  PROBLEM_MIN_FARMERS,
  PROBLEM_WINDOW_DAYS,
  MIN_FARMERS,
  MIN_SALES,
} from "@/lib/types";

const PRICE_DROP_PCT = Math.round((1 - PRICE_LOW_INDEX) * 100);

const SECTIONS: { title: string; items: string[] }[] = [
  {
    title: "Data sources",
    items: [
      "Hotline records (farmers, sales, problems): Supabase database.",
      "National price reference: UCDA / MAAIF monthly farm-gate CSV.",
      "Weather: Open-Meteo (CC BY 4.0).",
      "Map tiles: © OpenStreetMap contributors.",
    ],
  },
  {
    title: "Warning rules",
    items: [
      `Problem warning: the same problem is reported by at least ${PROBLEM_MIN_FARMERS} different farmers in one parish within ${PROBLEM_WINDOW_DAYS} days, and it was rare (at most 1 report) in the ${PROBLEM_BASELINE_WEEKS} weeks before.`,
      `Price warning: a district's median price over the last ${PRICE_WINDOW_DAYS} days is at least ${PRICE_DROP_PCT}% below the national reference.`,
      `A median is only shown with at least ${MIN_SALES} sales from at least ${MIN_FARMERS} different farmers.`,
    ],
  },
  {
    title: "Privacy",
    items: [
      "Only first names are shown.",
      "PINs and phone numbers never leave the database.",
      "Synthetic records are labelled as such.",
      "Access to this dashboard is protected with Basic authentication.",
    ],
  },
  {
    title: "About",
    items: ["Uganda Kiswahili coffee hotline dashboard.", "Hack-Nation × World Bank 2026."],
  },
];

export default function SettingsView() {
  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6 max-w-3xl">
      <p className="text-sm text-gray-500">Read-only reference for how this dashboard gets and shows its data.</p>
      {SECTIONS.map((section) => (
        <section key={section.title} className="bg-white border border-line rounded-xl overflow-hidden">
          <h2 className="px-4 py-3 border-b border-line text-base font-semibold text-ink">{section.title}</h2>
          <ul className="px-4 py-3 flex flex-col gap-2 text-sm text-gray-600 list-disc list-inside">
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
