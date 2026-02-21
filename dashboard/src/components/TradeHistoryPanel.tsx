"use client";

import { Card } from "./Card";
import { useTrades } from "@/hooks/useTrades";
import { formatUsd, formatTimestamp } from "@/lib/formatters";
import { clsx } from "clsx";
import Link from "next/link";

export function TradeHistoryPanel() {
  const { data, isLoading } = useTrades(10, 0);

  if (isLoading || !data) {
    return (
      <Card className="col-span-12">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-28 rounded bg-border-card" />
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-8 rounded bg-border-card" />
          ))}
        </div>
      </Card>
    );
  }

  if (data.trades.length === 0) {
    return (
      <Card className="col-span-12">
        <h2 className="mb-4 text-sm font-medium text-text-secondary">
          Recent Trades
        </h2>
        <div className="flex h-24 items-center justify-center text-sm text-text-muted">
          No trades yet
        </div>
      </Card>
    );
  }

  return (
    <Card className="col-span-12">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-text-secondary">
          Recent Trades
        </h2>
        {data.total > 10 && (
          <Link
            href="/trades"
            className="text-xs text-cyan hover:text-cyan/80 transition-colors"
          >
            View All ({data.total})
          </Link>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border-card text-text-muted">
              <th className="pb-2 text-left font-medium">#</th>
              <th className="pb-2 text-left font-medium">Time</th>
              <th className="pb-2 text-left font-medium">Side</th>
              <th className="pb-2 text-right font-medium">Amount</th>
              <th className="pb-2 text-right font-medium">Price</th>
              <th className="pb-2 text-right font-medium">Confidence</th>
              <th className="pb-2 text-left font-medium">Outcome</th>
              <th className="pb-2 text-right font-medium">Payout</th>
              <th className="pb-2 text-right font-medium">P&L</th>
            </tr>
          </thead>
          <tbody>
            {data.trades.map((trade) => {
              const pnl =
                trade.outcome === "win"
                  ? trade.payout - trade.amount_usdc
                  : trade.outcome === "loss"
                  ? -trade.amount_usdc
                  : 0;

              return (
                <tr
                  key={trade.id}
                  className="border-b border-border-card/50 hover:bg-border-card/20"
                >
                  <td className="py-2 stat-value text-text-muted">
                    {trade.id}
                  </td>
                  <td className="py-2 stat-value">
                    {formatTimestamp(trade.timestamp)}
                  </td>
                  <td className="py-2">
                    <span
                      className={clsx(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        trade.side === "Up"
                          ? "bg-green/15 text-green"
                          : "bg-red/15 text-red"
                      )}
                    >
                      {trade.side}
                    </span>
                  </td>
                  <td className="py-2 text-right stat-value">
                    {formatUsd(trade.amount_usdc)}
                  </td>
                  <td className="py-2 text-right stat-value">
                    ${trade.price.toFixed(3)}
                  </td>
                  <td className="py-2 text-right stat-value text-purple">
                    {(trade.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="py-2">
                    <span
                      className={clsx(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        trade.outcome === "win"
                          ? "bg-green/15 text-green"
                          : trade.outcome === "loss"
                          ? "bg-red/15 text-red"
                          : "bg-amber/15 text-amber"
                      )}
                    >
                      {trade.outcome}
                    </span>
                  </td>
                  <td className="py-2 text-right stat-value">
                    {trade.payout > 0 ? formatUsd(trade.payout) : "—"}
                  </td>
                  <td
                    className={clsx(
                      "py-2 text-right stat-value",
                      pnl > 0 ? "text-green" : pnl < 0 ? "text-red" : "text-text-muted"
                    )}
                  >
                    {trade.outcome === "pending"
                      ? "—"
                      : pnl >= 0
                      ? `+${formatUsd(pnl)}`
                      : `-${formatUsd(Math.abs(pnl))}`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
