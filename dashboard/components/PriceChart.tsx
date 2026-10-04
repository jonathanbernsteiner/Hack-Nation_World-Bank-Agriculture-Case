"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AreaSummary } from "@/lib/types";
import { formatMonth, formatUgx, labelForm } from "@/lib/format";

const CHART_HEIGHT = 220;
const TICK = { fontSize: 12, fill: "#94A3B8" };

interface PriceChartProps {
  area: AreaSummary;
}

export default function PriceChart({ area }: PriceChartProps) {
  const { mainForm, monthly } = area;
  const hasData = mainForm !== null && monthly.some((p) => p.median !== null);

  return (
    <div>
      <h2 className="text-base font-semibold text-ink mb-4">
        {mainForm ? `Price per kg: ${labelForm(mainForm)}` : "Price per kg"}
      </h2>
      {!hasData ? (
        <p className="text-sm text-faint text-center py-10">Price history appears once farmers report sales.</p>
      ) : (
        <div style={{ height: CHART_HEIGHT }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={monthly} margin={{ top: 15, right: 20, left: 20, bottom: 0 }}>
              <CartesianGrid stroke="#F1F5F9" vertical={false} />
              <XAxis dataKey="month" tickFormatter={formatMonth} axisLine={false} tickLine={false} tick={TICK} />
              <YAxis
                width={40}
                domain={["auto", "auto"]}
                axisLine={false}
                tickLine={false}
                tick={TICK}
                tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
              />
              <Tooltip
                labelFormatter={(label) => formatMonth(String(label))}
                formatter={(value, name) => [`${formatUgx(typeof value === "number" ? value : null)}/kg`, String(name)]}
                contentStyle={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, fontSize: 13 }}
              />
              <Legend
                iconType="circle"
                wrapperStyle={{ fontSize: 12 }}
                formatter={(value) => <span className="text-gray-600">{value}</span>}
              />
              <Line
                type="monotone"
                dataKey="median"
                name="This area"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="national"
                name="National"
                stroke="#94A3B8"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
