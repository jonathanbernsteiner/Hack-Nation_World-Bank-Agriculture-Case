const SECTIONS: { title: string; items: string[] }[] = [
  {
    title: "Sources",
    items: [
      "Hotline calls",
      "National prices: UCDA / MAAIF monthly CSV",
      "Weather: Open-Meteo; map: OpenStreetMap",
    ],
  },
  {
    title: "Privacy",
    items: [
      "First names only",
      "PINs and phone numbers stay in the database",
      "No export of individual records",
    ],
  },
];

function List({ items }: { items: string[] }) {
  return (
    <ul className="bg-white border border-line rounded-xl px-6 py-4 flex flex-col gap-1.5 text-sm text-gray-600 list-disc list-inside">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default function DataView() {
  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">Data</h1>
      {SECTIONS.map((section) => (
        <section key={section.title}>
          <h2 className="text-base font-semibold text-ink mb-3">{section.title}</h2>
          <List items={section.items} />
        </section>
      ))}
    </div>
  );
}
