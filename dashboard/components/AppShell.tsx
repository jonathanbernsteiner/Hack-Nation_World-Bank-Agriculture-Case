"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AlertTriangle, LayoutDashboard, Map as MapIcon, MapPin, PhoneCall, Settings, TrendingUp, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import GlobalSearch from "./GlobalSearch";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/call", label: "Live call", icon: PhoneCall },
  { href: "/map", label: "Map", icon: MapIcon },
  { href: "/areas", label: "Areas", icon: MapPin },
  { href: "/farmers", label: "Farmers", icon: Users },
  { href: "/prices", label: "Prices", icon: TrendingUp },
  { href: "/warnings", label: "Warnings", icon: AlertTriangle },
  { href: "/settings", label: "Settings", icon: Settings },
];

const MAIN_NAV = NAV.filter((item) => item.href !== "/settings");
const SETTINGS_NAV = NAV.filter((item) => item.href === "/settings");


function SideLink({ item, pathname }: { item: NavItem; pathname: string }) {
  const { href, label, icon: Icon } = item;
  const active = isActive(pathname, href);
  return (
    <div className="h-12 w-14 flex items-center justify-center">
      <Link
        href={href}
        aria-label={label}
        aria-current={active ? "page" : undefined}
        className={`group relative w-10 h-10 rounded-lg flex items-center justify-center transition-colors hover:bg-[#3B82F6] ${
          active ? "bg-[#3B82F6]" : ""
        }`}
      >
        <Icon size={22} color="#ffffff" />
        <span className="pointer-events-none absolute left-full top-1/2 -translate-y-1/2 ml-4 z-50 whitespace-nowrap rounded-md bg-ink text-white text-[13px] font-medium px-3 py-1.5 shadow-[0_2px_8px_rgba(0,0,0,0.3)] opacity-0 group-hover:opacity-100 group-hover:delay-200 transition-opacity">
          {label}
        </span>
      </Link>
    </div>
  );
}

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "/";
  const current = NAV.find((item) => isActive(pathname, item.href));

  return (
    <>
      <aside className="fixed top-0 left-0 h-screen w-14 bg-navy z-40 hidden md:flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-white text-navy text-sm font-bold flex items-center justify-center mt-3 mb-4">
          C
        </div>
        <nav className="flex flex-col">
          {MAIN_NAV.map((item) => (
            <SideLink key={item.href} item={item} pathname={pathname} />
          ))}
        </nav>
        <div className="mt-auto mb-1">
          {SETTINGS_NAV.map((item) => (
            <SideLink key={item.href} item={item} pathname={pathname} />
          ))}
        </div>
      </aside>

      <header className="fixed top-0 left-0 md:left-14 right-0 h-14 z-50 bg-white border-b border-line px-4 md:px-6 flex items-center justify-between">
        <div className="flex items-baseline gap-3 min-w-0 max-w-[25%] lg:max-w-[22%]">
          <p className="text-lg font-semibold text-ink truncate">{current?.label ?? "Overview"}</p>
        </div>
        <GlobalSearch />
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

      <main className="min-h-screen bg-surface pt-14 pb-16 md:pb-0 md:ml-14">
        {children}
      </main>
    </>
  );
}
