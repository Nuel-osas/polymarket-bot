import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { BalanceData } from "@/lib/types";

export function useBalance() {
  return useSWR<BalanceData>("/api/balance", fetcher, {
    refreshInterval: 5000,
  });
}
