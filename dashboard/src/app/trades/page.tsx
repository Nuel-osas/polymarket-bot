"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import { Card } from "@/components/Card";
import { useTrades } from "@/hooks/useTrades";
import { formatUsd, formatTimestamp } from "@/lib/formatters";
import { clsx } from "clsx";
import Link from "next/link";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 25;

export default function TradesPage() {
  const [page, setPage] = useState(0);
  const { data, isLoading } = useTrades(PAGE_SIZE, page * PAGE_SIZE);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl p-6">
        <div className="mb-4 flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1 text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
          <h2 className="text-lg font-bold">Trade History</h2>
          {data && (
            <span className="text-sm text-text-muted">
              ({data.total} total)
            </span>
          )}
        </div>

        <Card>
          {isLoading || !data ? (
            <div className="animate-pulse space-y-3">
              {[...Array(10)].map((_, i) => (
                <div key={i} className="h-8 rounded bg-border-card" />
              ))}
            </div>
          ) : data.trades.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-sm text-text-muted">
              No trades recorded yet
            </div>
          ) : (
            <>
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
                      <th className="pb-2 text-left font-medium">Mode</th>
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
                          <td className="py-2.5 stat-value text-text-muted">
                            {trade.id}
                          </td>
                          <td className="py-2.5 stat-value">
                            {formatTimestamp(trade.timestamp)}
                          </td>
                          <td className="py-2.5">
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
                          <td className="py-2.5 text-right stat-value">
                            {formatUsd(trade.amount_usdc)}
                          </td>
                          <td className="py-2.5 text-right stat-value">
                            ${trade.price.toFixed(3)}
                          </td>
                          <td className="py-2.5 text-right stat-value text-purple">
                            {(trade.confidence * 100).toFixed(0)}%
                          </td>
                          <td className="py-2.5">
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
                          <td className="py-2.5 text-right stat-value">
                            {trade.payout > 0 ? formatUsd(trade.payout) : "—"}
                          </td>
                          <td
                            className={clsx(
                              "py-2.5 text-right stat-value",
                              pnl > 0
                                ? "text-green"
                                : pnl < 0
                                ? "text-red"
                                : "text-text-muted"
                            )}
                          >
                            {trade.outcome === "pending"
                              ? "—"
                              : pnl >= 0
                              ? `+${formatUsd(pnl)}`
                              : `-${formatUsd(Math.abs(pnl))}`}
                          </td>
                          <td className="py-2.5">
                            {trade.dry_run && (
                              <span className="text-xs text-amber">DRY</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-4 flex items-center justify-between border-t border-border-card pt-4">
                  <span className="text-xs text-text-muted">
                    Page {page + 1} of {totalPages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      disabled={page === 0}
                      className="flex items-center gap-1 rounded-lg border border-border-card px-3 py-1.5 text-xs text-text-secondary transition-colors hover:bg-border-card disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="h-3 w-3" />
                      Prev
                    </button>
                    <button
                      onClick={() =>
                        setPage((p) => Math.min(totalPages - 1, p + 1))
                      }
                      disabled={page >= totalPages - 1}
                      className="flex items-center gap-1 rounded-lg border border-border-card px-3 py-1.5 text-xs text-text-secondary transition-colors hover:bg-border-card disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Next
                      <ChevronRight className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </main>
    </div>
  );
}
