"use client";

import { Card } from "./Card";
import { useRisk } from "@/hooks/useRisk";
import { formatUsd, formatTime } from "@/lib/formatters";
import { clsx } from "clsx";
import { Shield, AlertTriangle } from "lucide-react";

export function RiskPanel() {
  const { data, isLoading } = useRisk();

  if (isLoading || !data) {
    return (
      <Card className="col-span-4">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-20 rounded bg-border-card" />
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-8 rounded bg-border-card" />
          ))}
        </div>
      </Card>
    );
  }

  const drawdownPct = Math.max(0, data.drawdown);
  const drawdownColor =
    drawdownPct < 20 ? "bg-green" : drawdownPct < 40 ? "bg-amber" : "bg-red";

  return (
    <Card className="col-span-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-text-secondary">Risk</h2>
        {data.can_trade ? (
          <Shield className="h-4 w-4 text-green" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-red" />
        )}
      </div>

      {/* Can trade indicator */}
      <div className="mb-4 flex items-center gap-2">
        <div
          className={clsx(
            "h-3 w-3 rounded-full",
            data.can_trade ? "bg-green" : "bg-red"
          )}
        />
        <span className="text-sm">
          {data.can_trade ? "Can Trade" : data.reason.replace(/_/g, " ")}
        </span>
      </div>

      {/* Drawdown bar */}
      <div className="mb-4">
        <div className="mb-1 flex justify-between text-xs text-text-muted">
          <span>Drawdown</span>
          <span className="stat-value">
            {drawdownPct.toFixed(1)}% / {data.drawdown_limit}%
          </span>
        </div>
        <div className="h-2 rounded-full bg-border-card">
          <div
            className={clsx("h-2 rounded-full transition-all", drawdownColor)}
            style={{
              width: `${Math.min((drawdownPct / data.drawdown_limit) * 100, 100)}%`,
            }}
          />
        </div>
      </div>

      {/* Consecutive losses */}
      <div className="mb-4">
        <div className="mb-1 text-xs text-text-muted">Consecutive Losses</div>
        <div className="flex gap-1.5">
          {Array.from({ length: data.max_consecutive_losses }).map((_, i) => (
            <div
              key={i}
              className={clsx(
                "h-3 w-3 rounded-full",
                i < data.consecutive_losses ? "bg-red" : "bg-border-card"
              )}
            />
          ))}
        </div>
      </div>

      {/* Cooldown */}
      {data.cooldown_remaining > 0 && (
        <div className="mb-4 rounded-lg border border-amber/30 bg-amber/10 px-3 py-2">
          <div className="text-xs text-amber">
            Cooldown: {formatTime(data.cooldown_remaining)}
          </div>
        </div>
      )}

      {/* Position tier + bet size */}
      <div className="space-y-2 border-t border-border-card pt-3">
        <div className="flex justify-between text-xs">
          <span className="text-text-muted">Position Tier</span>
          <span className="stat-value text-text-primary">{data.position_tier}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-text-muted">Next Bet</span>
          <span className="stat-value text-cyan">{formatUsd(data.next_bet_size)}</span>
        </div>
      </div>
    </Card>
  );
}
