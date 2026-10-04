"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Maximize2, Minimize2, X } from "lucide-react";

const ICON_BTN = "p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";

interface SidePanelProps {
  title: string;
  open: boolean;
  onClose: () => void;
  link?: { href: string; label: string };
  children: ReactNode;
}

export default function SidePanel({ title, open, onClose, link, children }: SidePanelProps) {
  const [isFull, setIsFull] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: 0 });
  }, [title]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  const position = isFull ? "left-0 md:left-14 w-auto right-0" : "right-0 left-auto";
  return (
    <aside
      aria-label={title}
      style={isFull ? undefined : { width: "min(max(880px, 62vw), calc(100vw - 56px))" }}
      className={`fixed top-14 bottom-0 ${position} bg-white border-l border-line shadow-xl z-40 flex flex-col transition-[width,left] duration-150`}
    >
      <div className="flex items-center justify-between gap-3 p-5 border-b border-line">
        <h2 className="text-lg font-semibold text-gray-900 truncate">{title}</h2>
        <div className="flex items-center gap-1 shrink-0">
          {link && (
            <Link href={link.href} className="mr-2 text-sm font-medium text-accent hover:underline whitespace-nowrap">
              {link.label} →
            </Link>
          )}
          <button type="button" className={ICON_BTN} aria-label={isFull ? "Shrink panel" : "Expand panel"} onClick={() => setIsFull(!isFull)}>
            {isFull ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <button type="button" className={ICON_BTN} aria-label="Close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
      </div>
      <div ref={bodyRef} className="flex-1 overflow-y-auto p-6 bg-white">{children}</div>
    </aside>
  );
}
