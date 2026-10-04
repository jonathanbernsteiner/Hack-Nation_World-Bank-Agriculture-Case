"use client";

import { LayoutDashboard, Loader2, MapPin, Search, User, type LucideIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  areaHref,
  emptySearch,
  farmerHref,
  MIN_QUERY,
  type SearchResponse,
} from "@/lib/search";

const DEBOUNCE_MS = 200;

interface Row {
  key: string;
  group: "Pages" | "Areas" | "Farmers";
  icon: LucideIcon;
  label: string;
  secondary: string;
  href: string;
}

function toRows(r: SearchResponse): Row[] {
  return [
    ...r.pages.map((p): Row => ({
      key: `p:${p.href}`, group: "Pages", icon: LayoutDashboard, label: p.label, secondary: "", href: p.href,
    })),
    ...r.areas.map((a): Row => ({
      key: `a:${a.level}:${a.path.join("|")}`, group: "Areas", icon: MapPin, label: a.name, secondary: a.parent, href: areaHref(a),
    })),
    ...r.farmers.map((f): Row => ({
      key: `f:${f.id}`, group: "Farmers", icon: User, label: f.firstName, secondary: `${f.village} · ${f.district}`, href: farmerHref(f),
    })),
  ];
}

export default function GlobalSearch() {
  const router = useRouter();
  const rootRef = useRef<HTMLFormElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse>(emptySearch());
  const [active, setActive] = useState(-1);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const query = text.trim();
  const searchable = query.length >= MIN_QUERY;
  const rows = useMemo(() => toRows(results), [results]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    const onDown = (e: MouseEvent) => {
      if (rootRef.current?.contains(e.target as Node)) return;
      setOpen(false);
      setIsMobileOpen(false);
    };
    window.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown);
    };
  }, []);

  useEffect(() => {
    if (!searchable) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal: controller.signal });
        if (!res.ok) throw new Error("search failed");
        const next = (await res.json()) as SearchResponse;
        setResults(next);
        // Highlight the first result so Enter opens it (like OrbitFlow's search).
        setActive(next.pages.length + next.areas.length + next.farmers.length > 0 ? 0 : -1);
        setLoading(false);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setResults(emptySearch());
        setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, searchable]);

  useEffect(() => {
    if (isMobileOpen) inputRef.current?.focus();
  }, [isMobileOpen]);

  const go = (href: string) => {
    setOpen(false);
    setIsMobileOpen(false);
    (document.activeElement as HTMLElement | null)?.blur();
    router.push(href);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setOpen(false);
      setIsMobileOpen(false);
      inputRef.current?.blur();
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!rows.length) return;
      e.preventDefault();
      setOpen(true);
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActive((i) => (i + step + rows.length) % rows.length);
    }
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const row = open && searchable ? rows[active] : undefined;
    if (row) return go(row.href);
    go(query ? `/farmers?q=${encodeURIComponent(query)}` : "/farmers");
  };

  const showPanel = open && searchable;
  const groups = (["Pages", "Areas", "Farmers"] as const)
    .map((g) => ({ g, items: rows.map((r, i) => ({ r, i })).filter(({ r }) => r.group === g) }))
    .filter((x) => x.items.length > 0);

  const formLayout = isMobileOpen ? "flex fixed top-[60px] inset-x-4 z-[60] shadow-lg" : "hidden";
  return (
    <>
    <button
      type="button"
      aria-label="Search"
      onClick={() => setIsMobileOpen(true)}
      className="sm:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100"
    >
      <Search size={20} />
    </button>
    <form
      ref={rootRef}
      role="search"
      className={`${formLayout} sm:flex sm:absolute sm:inset-x-auto sm:top-auto sm:left-1/2 sm:-translate-x-1/2 sm:shadow-none sm:w-72 md:w-80 xl:w-96 h-10 rounded-3xl border border-[#CBD5E1] bg-white items-center gap-2 px-4 focus-within:border-accent`}
      onSubmit={onSubmit}
    >
      <Search size={18} color="#94A3B8" className="shrink-0" />
      <input
        ref={inputRef}
        type="search"
        role="combobox"
        aria-expanded={showPanel}
        aria-controls="global-search-results"
        aria-autocomplete="list"
        aria-label="Search farmers, villages, districts"
        placeholder="Search farmers, villages, districts"
        value={text}
        autoComplete="off"
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className="w-full bg-transparent text-sm text-ink placeholder:text-faint outline-none"
      />
      {showPanel && (
        <div
          id="global-search-results"
          role="listbox"
          className="absolute top-full mt-2 w-[min(560px,90vw)] left-1/2 -translate-x-1/2 bg-white border border-line rounded-xl shadow-lg p-2 z-[60] max-h-[70vh] overflow-auto"
        >
          {loading && (
            <div className="flex items-center gap-2 px-2 py-2 text-sm text-muted">
              <Loader2 size={16} className="animate-spin" /> Searching
            </div>
          )}
          {!loading && rows.length === 0 && <div className="px-2 py-2 text-sm text-muted">No results</div>}
          {!loading &&
            groups.map(({ g, items }) => (
              <div key={g}>
                <div className="text-xs font-medium text-muted px-2 py-1">{g}</div>
                {items.map(({ r, i }) => (
                  <button
                    key={r.key}
                    type="button"
                    role="option"
                    aria-selected={i === active}
                    onMouseEnter={() => setActive(i)}
                    onClick={() => go(r.href)}
                    className={`w-full text-left flex items-center gap-2 px-2 py-2 rounded-md text-sm ${i === active ? "bg-gray-50" : ""}`}
                  >
                    <r.icon size={16} className="shrink-0 text-muted" />
                    <span className="text-ink truncate">{r.label}</span>
                    {r.secondary && <span className="text-muted truncate">{r.secondary}</span>}
                  </button>
                ))}
              </div>
            ))}
        </div>
      )}
    </form>
    </>
  );
}
