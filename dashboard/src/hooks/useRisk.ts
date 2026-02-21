import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { RiskData } from "@/lib/types";

export function useRisk() {
  return useSWR<RiskData>("/api/risk", fetcher, {
    refreshInterval: 3000,
  });
}
