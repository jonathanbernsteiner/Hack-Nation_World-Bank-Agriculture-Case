"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { AlertTriangle, LayoutDashboard, LogOut, Map as MapIcon, Search, Settings, TrendingUp, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/map", label: "Map", icon: MapIcon },
  { href: "/farmers", label: "Farmers", icon: Users },
  { href: "/prices", label: "Prices", icon: TrendingUp },
  { href: "/warnings", label: "Warnings", icon: AlertTriangle },
  { href: "/settings", label: "Settings", icon: Settings },
];

const MAIN_NAV = NAV.filter((item) => item.href !== "/settings");
const SETTINGS_NAV = NAV.filter((item) => item.href === "/settings");

function SearchPill() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <form
      role="search"
      className="absolute left-1/2 -translate-x-1/2 w-48 sm:w-72 md:w-96 h-10 rounded-3xl border border-[#CBD5E1] bg-white flex items-center gap-2 px-4 focus-within:border-accent"
      onSubmit={(e) => {
        e.preventDefault();
        const q = inputRef.current?.value.trim() ?? "";
        router.push(q ? `/farmers?q=${encodeURIComponent(q)}` : "/farmers");
      }}
    >
      <Search size={18} color="#94A3B8" className="shrink-0" />
      <input
        ref={inputRef}
        type="search"
        aria-label="Search farmers, villages, districts"
        placeholder="Search farmers, villages, districts"
        className="w-full bg-transparent text-sm text-ink placeholder:text-faint outline-none"
        onKeyDown={(e) => {
          if (e.key === "Escape") inputRef.current?.blur();
        }}
      />
    </form>
  );
}

function SideLink({ item, pathname }: { item: NavItem; pathname: string }) {
  const { href, label, icon: Icon } = item;
  const active = isActive(pathname, href);
  return (
    <Link
      href={href}
      aria-label={label}
      aria-current={active ? "page" : undefined}
      className={`group relative w-10 h-10 rounded-lg flex items-center justify-center transition-colors hover:bg-accent ${
        active ? "bg-accent" : ""
      }`}
    >
      <Icon size={22} color={active ? "#ffffff" : "#94A3B8"} className="group-hover:!text-white" />
      <span className="pointer-events-none absolute left-full ml-2 whitespace-nowrap rounded-md bg-ink text-white text-[13px] font-medium px-3 py-1.5 shadow-[0_2px_8px_rgba(0,0,0,0.3)] opacity-0 group-hover:opacity-100 group-hover:delay-200 transition-opacity">
        {label}
      </span>
    </Link>
  );
}

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppShell({ children, hasSynthetic }: { children: React.ReactNode; hasSynthetic?: boolean }) {
  const pathname = usePathname() ?? "/";
  const current = NAV.find((item) => isActive(pathname, item.href));

  return (
    <>
      <aside className="fixed top-0 left-0 h-screen w-14 bg-navy z-40 hidden md:flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-white text-navy text-sm font-bold flex items-center justify-center mt-3 mb-4">
          C
        </div>
        <nav className="flex flex-col gap-1">
          {MAIN_NAV.map((item) => (
            <SideLink key={item.href} item={item} pathname={pathname} />
          ))}
        </nav>
        <div className="mt-auto mb-3">
          {SETTINGS_NAV.map((item) => (
            <SideLink key={item.href} item={item} pathname={pathname} />
          ))}
        </div>
      </aside>

      <header className="fixed top-0 left-0 md:left-14 right-0 h-14 z-50 bg-white border-b border-line px-4 md:px-6 flex items-center justify-between">
        <div className="flex items-baseline gap-3 min-w-0 max-w-[30%] lg:max-w-none">
          <h1 className="text-lg font-semibold text-ink truncate">{current?.label ?? "Coffee hotline"}</h1>
          <span className="text-sm text-faint hidden 2xl:inline">Uganda · Kiswahili coffee hotline</span>
        </div>
        <SearchPill />
        <div className="flex items-center gap-3 shrink-0 ml-auto">
          {hasSynthetic && (
            <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]">
              Synthetic data
            </span>
          )}
          <a
            href="/api/logout"
            className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <LogOut size={16} />
            <span className="hidden sm:inline">Sign out</span>
          </a>
        </div>
      </header>

      <nav className="fixed bottom-0 inset-x-0 h-14 bg-navy z-40 md:hidden flex justify-around">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className="flex flex-col items-center justify-center gap-0.5 flex-1"
              style={{ color: active ? "#3B82F6" : "#94A3B8" }}
            >
              <Icon size={20} />
              <span className="text-[10px]">{label}</span>
            </Link>
          );
        })}
      </nav>

      <main className="min-h-screen bg-surface pt-14 pb-16 md:pb-0 md:ml-14">{children}</main>
    </>
  );
}
