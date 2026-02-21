"use client";

import { Header } from "@/components/Header";
import { HeroPanel } from "@/components/HeroPanel";
import { LivePricePanel } from "@/components/LivePricePanel";
import { SignalPanel } from "@/components/SignalPanel";
import { EquityCurvePanel } from "@/components/EquityCurvePanel";
import { RiskPanel } from "@/components/RiskPanel";
import { TradeHistoryPanel } from "@/components/TradeHistoryPanel";

export default function Home() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl p-6">
        <div className="grid grid-cols-12 gap-4">
          {/* Row 1: Hero + Live Price + Signal */}
          <HeroPanel />
          <LivePricePanel />
          <SignalPanel />

          {/* Row 2: Equity Curve + Risk */}
          <EquityCurvePanel />
          <RiskPanel />

          {/* Row 3: Trade History */}
          <TradeHistoryPanel />
        </div>
      </main>
    </div>
  );
}
