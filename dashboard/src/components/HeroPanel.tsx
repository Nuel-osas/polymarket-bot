"use client";

import { DollarSign, TrendingUp, Target, Zap } from "lucide-react";
import { Card } from "./Card";
import { useStatus } from "@/hooks/useStatus";
import { formatUsd, formatPercent, formatPnl } from "@/lib/formatters";

function StatCard({
  label,
  value,
  subtitle,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-xs text-text-muted uppercase tracking-wider">
        <Icon className={`h-3.5 w-3.5 ${color}`} />
        {label}
      </div>
      <div className={`stat-value text-xl ${color}`}>{value}</div>
      {subtitle && (
        <div className="text-xs text-text-muted">{subtitle}</div>
      )}
    </div>
  );
}

export function HeroPanel() {
  const { data, isLoading } = useStatus();

  if (isLoading || !data) {
    return (
      <Card className="col-span-4">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-24 rounded bg-border-card" />
          <div className="grid grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-16 rounded bg-border-card" />
            ))}
          </div>
        </div>
      </Card>
    );
  }

  const pnl = data.balance - (data.peak_balance > 0 ? data.balance : 0);
  const pnlFromStart = data.balance - (data.peak_balance - (data.peak_balance - data.balance));

  return (
    <Card className="col-span-4">
      <h2 className="mb-4 text-sm font-medium text-text-secondary">Overview</h2>
      <div className="grid grid-cols-2 gap-5">
        <StatCard
          label="Balance"
          value={formatUsd(data.balance)}
          subtitle={`Peak: ${formatUsd(data.peak_balance)}`}
          icon={DollarSign}
          color="text-green"
        />
        <StatCard
          label="P&L"
          value={formatPnl(data.balance - data.peak_balance + (data.peak_balance - data.balance))}
          subtitle={`${data.total_trades} trades`}
          icon={TrendingUp}
          color={data.balance >= data.peak_balance ? "text-green" : "text-red"}
        />
        <StatCard
          label="Win Rate"
          value={formatPercent(data.win_rate)}
          subtitle={`W ${data.wins} / L ${data.losses}`}
          icon={Target}
          color="text-cyan"
        />
        <StatCard
          label="Signals"
          value={`${data.signals_traded}/${data.total_signals}`}
          subtitle="traded / detected"
          icon={Zap}
          color="text-purple"
        />
      </div>
    </Card>
  );
}
