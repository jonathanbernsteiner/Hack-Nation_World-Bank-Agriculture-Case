import { AlertTriangle, Phone, Scale, Users } from "lucide-react";
import type { ReactNode } from "react";
import { formatIndex, formatNumber } from "@/lib/format";
import type { Kpis } from "@/lib/types";

interface TileProps {
  icon: ReactNode;
  value: string;
  label: string;
  sub: string;
}

function Tile({ icon, value, label, sub }: TileProps) {
  return (
    <div className="bg-white border border-line rounded-xl p-5">
      <div className="flex items-center gap-2.5">
        <div
          className="w-8 h-8 shrink-0 rounded-full flex items-center justify-center"
          style={{ background: "rgba(59,130,246,0.1)" }}
        >
          {icon}
        </div>
        <div className="min-w-0 line-clamp-2" style={{ fontSize: 14, fontWeight: 500, color: "#64748B" }}>{label}</div>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "#0F172A", marginTop: 8 }}>{value}</div>
      <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 2 }}>{sub}</div>
    </div>
  );
}

function callsDelta(current: number, prev: number | undefined): string {
  if (prev === undefined) return "last 30 days";
  if (prev === 0) return "no calls before";
  const pct = Math.round((current / prev - 1) * 100);
  return `${pct >= 0 ? "+" : "−"}${Math.abs(pct)}% vs previous 30`;
}

export default function KpiRow({ kpis }: { kpis: Kpis }) {
  const icon = (Icon: typeof Users) => <Icon size={16} color="#3B82F6" />;
  const newSub = `+${formatNumber(kpis.newFarmers30d)} in 30 days`;
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Tile
        icon={icon(Users)}
        value={formatNumber(kpis.farmers)}
        label="Registered farmers"
        sub={newSub}
      />
      <Tile icon={icon(Phone)} value={formatNumber(kpis.callsLast30d)} label="Calls, 30 days" sub={callsDelta(kpis.callsLast30d, kpis.callsPrev30d)} />
      <Tile icon={icon(Scale)} value={formatIndex(kpis.priceIndex)} label="Price vs national, 90 days" sub="farmer-reported" />
      <Tile icon={icon(AlertTriangle)} value={formatNumber(kpis.activeWarnings)} label="Active warnings" sub="need an officer check" />
    </div>
  );
}
