"use client";

import { Card } from "./Card";
import { usePrice } from "@/hooks/usePrice";
import { formatBtcPrice, formatPercent } from "@/lib/formatters";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { ArrowUp, ArrowDown, Clock } from "lucide-react";
import { clsx } from "clsx";

export function LivePricePanel() {
  const { data, isLoading } = usePrice();

  if (isLoading || !data) {
    return (
      <Card className="col-span-4">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-20 rounded bg-border-card" />
          <div className="h-8 w-40 rounded bg-border-card" />
          <div className="h-24 rounded bg-border-card" />
        </div>
      </Card>
    );
  }

  const isPositive = data.momentum_pct >= 0;
  const momentumColor = isPositive ? "text-green" : "text-red";
  const fillColor = isPositive ? "#00d4aa" : "#ff4757";

  // Chart data: resample to 1-second intervals for smooth display
  const chartData = data.history.map((h) => ({
    time: new Date(h.ts).toLocaleTimeString("en-US", {
      minute: "2-digit",
      second: "2-digit",
    }),
    price: h.price,
  }));

  return (
    <Card className="col-span-4">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-sm font-medium text-text-secondary">BTC/USDT</h2>
        <div className="flex items-center gap-1 text-xs text-text-muted">
          <Clock className="h-3 w-3" />
          {data.window_size} ticks
        </div>
      </div>

      <div className="mb-3 flex items-baseline gap-3">
        <span className="stat-value text-2xl text-cyan">
          {formatBtcPrice(data.btc_price)}
        </span>
        <span className={clsx("stat-value text-sm", momentumColor)}>
          {isPositive ? (
            <ArrowUp className="inline h-3.5 w-3.5" />
          ) : (
            <ArrowDown className="inline h-3.5 w-3.5" />
          )}
          {formatPercent(Math.abs(data.momentum_pct * 100), 3)}
        </span>
      </div>

      {/* Pyth oracle comparison */}
      <div className="mb-3 flex items-center gap-4 rounded-lg bg-border-card/50 px-3 py-2 text-xs">
        <div>
          <span className="text-text-muted">Binance </span>
          <span className="stat-value text-cyan">{formatBtcPrice(data.btc_price)}</span>
        </div>
        <div>
          <span className="text-text-muted">Pyth </span>
          <span className="stat-value text-amber-400">
            {data.oracle_price > 0 ? formatBtcPrice(data.oracle_price) : "—"}
          </span>
        </div>
        <div className="ml-auto">
          <span className="text-text-muted">Divergence </span>
          <span className={clsx(
            "stat-value",
            data.oracle_divergence_pct > 0.0003 ? "text-green" : "text-text-muted"
          )}>
            {formatPercent(data.oracle_divergence_pct * 100, 4)}
          </span>
        </div>
        <div>
          <span className="text-text-muted">Lag </span>
          <span className={clsx(
            "stat-value",
            data.oracle_lag_seconds > 2 ? "text-green" : "text-text-muted"
          )}>
            {data.oracle_lag_seconds.toFixed(1)}s
          </span>
        </div>
      </div>

      {/* Momentum bar */}
      <div className="mb-3">
        <div className="relative h-2 rounded-full bg-border-card">
          <div
            className="absolute top-0 h-2 rounded-full transition-all"
            style={{
              backgroundColor: fillColor,
              width: `${Math.min(Math.abs(data.momentum_pct) / 0.003 * 100, 100)}%`,
              left: isPositive ? "50%" : undefined,
              right: isPositive ? undefined : "50%",
            }}
          />
          <div className="absolute left-1/2 top-0 h-2 w-px bg-text-muted" />
        </div>
      </div>

      {/* Price chart */}
      {chartData.length > 2 && (
        <div className="h-24">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={fillColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={fillColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" hide />
              <YAxis domain={["auto", "auto"]} hide />
              <Tooltip
                contentStyle={{
                  background: "#111827",
                  border: "1px solid #1e293b",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "#94a3b8" }}
                itemStyle={{ color: "#06b6d4" }}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke={fillColor}
                fill="url(#priceGradient)"
                strokeWidth={1.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Market info */}
      {data.market.active && (
        <div className="mt-3 flex items-center gap-4 text-xs text-text-muted">
          <span>
            Up: <span className="text-green stat-value">${data.market.up_price.toFixed(2)}</span>
          </span>
          <span>
            Down: <span className="text-red stat-value">${data.market.down_price.toFixed(2)}</span>
          </span>
          <span className="ml-auto">
            {data.market.window_remaining}s remaining
          </span>
        </div>
      )}
    </Card>
  );
}
