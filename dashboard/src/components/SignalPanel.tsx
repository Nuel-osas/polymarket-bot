"use client";

import { Card } from "./Card";
import { useSignal } from "@/hooks/useSignal";
import { clsx } from "clsx";
import { Radio, ArrowUpCircle, ArrowDownCircle } from "lucide-react";

function GateRow({
  label,
  passed,
  value,
  threshold,
  unit = "",
}: {
  label: string;
  passed: boolean;
  value: string;
  threshold: string;
  unit?: string;
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <div className="flex items-center gap-2">
        <div
          className={clsx(
            "h-2 w-2 rounded-full",
            passed ? "bg-green" : "bg-red/60"
          )}
        />
        <span className="text-xs text-text-secondary">{label}</span>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className="stat-value text-text-primary">
          {value}{unit}
        </span>
        <span className="text-text-muted">/ {threshold}{unit}</span>
      </div>
    </div>
  );
}

export function SignalPanel() {
  const { data, isLoading } = useSignal();

  if (isLoading || !data) {
    return (
      <Card className="col-span-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-24 rounded bg-border-card" />
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-6 rounded bg-border-card" />
          ))}
        </div>
      </Card>
    );
  }

  const { gates, active_signal } = data;

  return (
    <Card className="col-span-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-medium text-text-secondary">Signal Gates</h2>
        <Radio className="h-4 w-4 text-purple" />
      </div>

      <div className="space-y-0.5">
        <GateRow
          label="Timing"
          passed={gates.timing.passed}
          value={gates.timing.value.toFixed(0)}
          threshold={`${gates.timing.min}-${gates.timing.max}`}
          unit="s"
        />
        <GateRow
          label="Momentum"
          passed={gates.momentum.passed}
          value={gates.momentum.value.toFixed(4)}
          threshold={gates.momentum.threshold!.toFixed(4)}
          unit="%"
        />
        <GateRow
          label="Oracle Lag"
          passed={gates.oracle_lag.passed}
          value={gates.oracle_lag.value.toFixed(4)}
          threshold={gates.oracle_lag.threshold!.toFixed(4)}
          unit="%"
        />
        <div className="flex items-center justify-between py-1.5">
          <div className="flex items-center gap-2">
            <div
              className={clsx(
                "h-2 w-2 rounded-full",
                gates.dual_confirmation.passed ? "bg-green" : "bg-red/60"
              )}
            />
            <span className="text-xs text-text-secondary">Dual Confirm</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-text-muted">B:</span>
            <span className={clsx("stat-value", gates.dual_confirmation.binance_momentum >= 0 ? "text-green" : "text-red")}>
              {gates.dual_confirmation.binance_momentum.toFixed(4)}%
            </span>
            <span className="text-text-muted">P:</span>
            <span className={clsx("stat-value", gates.dual_confirmation.pyth_momentum >= 0 ? "text-green" : "text-red")}>
              {gates.dual_confirmation.pyth_momentum.toFixed(4)}%
            </span>
          </div>
        </div>
        <GateRow
          label="Market Price"
          passed={gates.market_price.passed}
          value={`$${gates.market_price.value.toFixed(3)}`}
          threshold={`$${gates.market_price.threshold!.toFixed(2)}`}
        />
        <GateRow
          label="Confidence"
          passed={gates.confidence.passed}
          value={gates.confidence.value.toFixed(2)}
          threshold={gates.confidence.threshold!.toFixed(2)}
        />
      </div>

      {/* Active signal card */}
      {active_signal && (
        <div className="mt-4 rounded-lg border border-purple/30 bg-purple/10 p-3">
          <div className="flex items-center gap-2">
            {active_signal.side === "Up" ? (
              <ArrowUpCircle className="h-5 w-5 text-green" />
            ) : (
              <ArrowDownCircle className="h-5 w-5 text-red" />
            )}
            <span className="text-sm font-semibold text-text-primary">
              {active_signal.side} Signal
            </span>
            <span className="ml-auto stat-value text-sm text-purple">
              {(active_signal.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-text-muted">
            <span>Price: ${active_signal.target_price.toFixed(3)}</span>
            <span>BTC: ${active_signal.binance_price.toFixed(2)}</span>
          </div>
        </div>
      )}

      <div className="mt-3 text-xs text-text-muted">
        {data.signals_traded}/{data.total_signals} signals traded
      </div>
    </Card>
  );
}
