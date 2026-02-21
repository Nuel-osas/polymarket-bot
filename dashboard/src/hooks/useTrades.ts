import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { TradesData } from "@/lib/types";

export function useTrades(limit = 10, offset = 0) {
  return useSWR<TradesData>(
    `/api/trades?limit=${limit}&offset=${offset}`,
    fetcher,
    { refreshInterval: 5000 }
  );
}
