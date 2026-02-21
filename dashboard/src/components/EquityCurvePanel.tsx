"use client";

import { Card } from "./Card";
import { useBalance } from "@/hooks/useBalance";
import { formatUsd } from "@/lib/formatters";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  ReferenceLine,
} from "recharts";

export function EquityCurvePanel() {
  const { data, isLoading } = useBalance();

  if (isLoading || !data) {
    return (
      <Card className="col-span-8">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-28 rounded bg-border-card" />
          <div className="h-48 rounded bg-border-card" />
        </div>
      </Card>
    );
  }

  const chartData = data.history.map((h) => ({
    time: new Date(h.timestamp * 1000).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    }),
    balance: h.balance,
  }));

  return (
    <Card className="col-span-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-text-secondary">Equity Curve</h2>
        <div className="flex items-center gap-4 text-xs">
          <span className="text-text-muted">
            Current: <span className="stat-value text-green">{formatUsd(data.current)}</span>
          </span>
          <span className="text-text-muted">
            Peak: <span className="stat-value text-cyan">{formatUsd(data.peak)}</span>
          </span>
        </div>
      </div>

      {chartData.length > 1 ? (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d4aa" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00d4aa" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="time"
                tick={{ fontSize: 10, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `$${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: "#111827",
                  border: "1px solid #1e293b",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "#94a3b8" }}
                formatter={(value) => [formatUsd(value as number), "Balance"]}
              />
              <ReferenceLine
                y={data.initial}
                stroke="#64748b"
                strokeDasharray="3 3"
                label={{
                  value: `Initial ${formatUsd(data.initial)}`,
                  position: "right",
                  fill: "#64748b",
                  fontSize: 10,
                }}
              />
              <Area
                type="monotone"
                dataKey="balance"
                stroke="#00d4aa"
                fill="url(#equityGradient)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="flex h-48 items-center justify-center text-sm text-text-muted">
          Waiting for balance history...
        </div>
      )}
    </Card>
  );
}
