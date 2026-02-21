"use client";

import { Activity } from "lucide-react";
import { useStatus } from "@/hooks/useStatus";
import { BotStateIndicator } from "./BotStateIndicator";
import { formatTime } from "@/lib/formatters";

export function Header() {
  const { data } = useStatus();

  return (
    <header className="flex items-center justify-between border-b border-border-card px-6 py-4">
      <div className="flex items-center gap-3">
        <Activity className="h-6 w-6 text-green" />
        <h1 className="text-lg font-bold tracking-tight">Polybot</h1>
        {data && <BotStateIndicator state={data.state} />}
        {data?.dry_run && (
          <span className="rounded-full border border-amber/40 bg-amber/10 px-2.5 py-0.5 text-xs font-medium text-amber">
            DRY RUN
          </span>
        )}
      </div>
      <div className="flex items-center gap-4 text-sm text-text-secondary">
        {data && <span>Uptime: {formatTime(data.uptime_seconds)}</span>}
        {!data && (
          <span className="text-text-muted">Connecting...</span>
        )}
      </div>
    </header>
  );
}
