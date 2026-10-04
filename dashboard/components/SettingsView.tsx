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
    title: "What this data does not cover",
    items: [
      "Only farmers who own or borrow a phone and call in Kiswahili. Kiswahili is a second language in most coffee districts, so coverage skews towards some groups, including by gender.",
      "Hotline callers are a small share of Uganda's ~2.8M coffee farms (MAAIF 2026: 1.2M still unmapped).",
      "Prices are self-reported by phone and not verified against receipts.",
      "Locations are village points, not plot GPS, so this is not EUDR-grade geolocation.",
      "Problems are suspected from phone descriptions, not confirmed in the field.",
      "The latest national reference month (Sep 2026) is carried forward for later months.",
      "Most records are synthetic.",
    ],
  },
  {
    title: "Warning rules",
    items: [
      `Problem warning: the same problem is reported by at least ${PROBLEM_MIN_FARMERS} different farms in one parish within ${PROBLEM_WINDOW_DAYS} days, and from more farms than in the ${PROBLEM_BASELINE_WEEKS} weeks before.`,
      `Price warning: a district's ${PRICE_WINDOW_DAYS}-day median price is at least ${PRICE_DROP_PCT}% below the national median, and needs at least ${MIN_SALES} sales from ${MIN_FARMERS} farmers.`,
      "A warning is a prompt for an extension officer to check, never an automatic action.",
    ],
  },
  {
    title: "Privacy",
    items: [
      "Only first names are shown.",
      "PINs and phone numbers never leave the database.",
      "No export of individual records.",
      "Synthetic records are labelled as such.",
      "Access to this dashboard is protected with Basic authentication.",
    ],
  },
  {
    title: "About",
    items: ["Uganda Kiswahili coffee hotline dashboard.", "Hack-Nation × World Bank 2026."],
  },
];

function List({ items }: { items: string[] }) {
  return (
    <ul className="bg-white border border-line rounded-xl p-6 flex flex-col gap-2 text-sm text-gray-600 list-disc list-inside">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default function SettingsView() {
  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">Data &amp; limits</h1>
      <section>
        <h2 className="text-base font-semibold text-ink mb-4">What this shows</h2>
        <p className="bg-white border border-line rounded-xl p-6 text-sm text-gray-600">
          A read-only view of what farmers tell the Kiswahili coffee hotline in Uganda: who calls, the prices they report,
          and the problems they describe. Patterns that look unusual are flagged so an extension officer can check them.
        </p>
      </section>
      {SECTIONS.map((section) => (
        <section key={section.title}>
          <h2 className="text-base font-semibold text-ink mb-4">{section.title}</h2>
          <List items={section.items} />
        </section>
      ))}
    </div>
  );
}
