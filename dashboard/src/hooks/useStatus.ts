import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { StatusData } from "@/lib/types";

export function useStatus() {
  return useSWR<StatusData>("/api/status", fetcher, {
    refreshInterval: 1000,
  });
}
