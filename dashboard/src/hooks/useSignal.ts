import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { SignalData } from "@/lib/types";

export function useSignal() {
  return useSWR<SignalData>("/api/signal", fetcher, {
    refreshInterval: 2000,
  });
}
