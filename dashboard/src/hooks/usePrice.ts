import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { PriceData } from "@/lib/types";

export function usePrice() {
  return useSWR<PriceData>("/api/price", fetcher, {
    refreshInterval: 1000,
  });
}
