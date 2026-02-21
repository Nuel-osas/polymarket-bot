import { clsx } from "clsx";

const stateColors: Record<string, string> = {
  SCANNING: "bg-green/20 text-green border-green/40",
  SIGNAL: "bg-purple/20 text-purple border-purple/40",
  TRADING: "bg-cyan/20 text-cyan border-cyan/40",
  WAITING: "bg-amber/20 text-amber border-amber/40",
  COMPOUNDING: "bg-green/20 text-green border-green/40",
  COOLDOWN: "bg-amber/20 text-amber border-amber/40",
  PAUSED: "bg-text-muted/20 text-text-muted border-text-muted/40",
  STOPPED: "bg-red/20 text-red border-red/40",
};

const pulseStates = new Set(["SCANNING", "TRADING", "WAITING"]);

export function BotStateIndicator({ state }: { state: string }) {
  const colors = stateColors[state] || stateColors.STOPPED;
  const shouldPulse = pulseStates.has(state);

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider",
        colors
      )}
    >
      <span
        className={clsx(
          "h-2 w-2 rounded-full bg-current",
          shouldPulse && "animate-pulse"
        )}
      />
      {state}
    </span>
  );
}
