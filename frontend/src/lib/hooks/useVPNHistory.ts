// frontend/src/lib/hooks/useVPNHistory.ts

import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";

export type VPNHistoryPoint = {
  ts: number;
  count: number;
};

export default function useVPNHistory() {
  return useQuery({
    queryKey: ["vpn-history"],
    queryFn: async () => {
      const res = await api.get("/vpn/history");
      const rows = res.data;

      const map: Record<number, number> = {};

      for (const r of rows) {
        const t = new Date(r.timestamp_logged).getTime();
        if (!map[t]) map[t] = 0;
        map[t] += 1;
      }

      return Object.entries(map)
        .map(([ts, count]) => ({
          ts: Number(ts),
          count: count as number,
        }))
        .sort((a, b) => a.ts - b.ts);
    },
  });
}