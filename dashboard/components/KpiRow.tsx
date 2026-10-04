import { AlertTriangle, Phone, TrendingUp, Users } from "lucide-react";
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
    <div className="bg-white border border-line rounded-xl p-6">
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center mb-4"
        style={{ background: "rgba(59,130,246,0.1)" }}
      >
        {icon}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "#0F172A" }}>{value}</div>
      <div style={{ fontSize: 14, fontWeight: 500, color: "#64748B", marginTop: 4 }}>{label}</div>
      <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 2 }}>{sub}</div>
    </div>
  );
}

export default function KpiRow({ kpis }: { kpis: Kpis }) {
  const icon = (Icon: typeof Users) => <Icon size={20} color="#3B82F6" />;
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Tile
        icon={icon(Users)}
        value={formatNumber(kpis.farmers)}
        label="Registered farmers"
        sub={`in ${kpis.villages} villages, ${kpis.districts} districts · +${kpis.newFarmers30d} in 30 days`}
      />
      <Tile
        icon={icon(Phone)}
        value={formatNumber(kpis.callsLast30d)}
        label="Calls in the last 30 days"
        sub="all registered farmers"
      />
      <Tile
        icon={icon(TrendingUp)}
        value={formatIndex(kpis.priceIndex)}
        label="Price vs national"
        sub="farmer-reported, last 90 days"
      />
      <Tile
        icon={icon(AlertTriangle)}
        value={formatNumber(kpis.activeWarnings)}
        label="Active warnings"
        sub="unusual reports and low prices"
      />
    </div>
  );
}
