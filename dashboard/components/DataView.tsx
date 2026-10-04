const SECTIONS: { title: string; items: string[] }[] = [
  {
    title: "Sources",
    items: [
      "Hotline records: Supabase database",
      "National prices: UCDA / MAAIF monthly CSV",
      "Weather: Open-Meteo; map: OpenStreetMap",
    ],
  },
  {
    title: "Limits",
    items: [
      "Only farmers with a phone who call in Kiswahili",
      "A small share of Uganda's ~2.8M coffee farms",
      "Prices are self-reported, not checked against receipts",
      "Village points, not plot GPS: not EUDR-grade",
      "Problems are suspected, not confirmed in the field",
      "Latest national reference month is carried forward",
    ],
  },
  {
    title: "Privacy",
    items: [
      "First names only",
      "PINs and phone numbers stay in the database",
      "No export of individual records",
      "Access protected with Basic authentication",
    ],
  },
];

function List({ items }: { items: string[] }) {
  return (
    <ul className="bg-white border border-line rounded-xl py-4 pr-5 flex flex-col gap-1.5 text-sm text-gray-600 list-disc pl-9">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default function DataView() {
  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">Data &amp; limits</h1>
      {SECTIONS.map((section) => (
        <section key={section.title}>
          <h2 className="text-base font-semibold text-ink mb-3">{section.title}</h2>
          <List items={section.items} />
        </section>
      ))}
    </div>
  );
}
