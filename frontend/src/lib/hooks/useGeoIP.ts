// frontend/src/lib/hooks/useGeoIP.ts

import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";

export default function useGeoIP(ip?: string | null) {
  return useQuery({
    queryKey: ["geoip", ip],
    enabled: !!ip,
    queryFn: async () => {
      if (!ip) return null;
      const res = await api.get(`/vpn/geoip?ip=${encodeURIComponent(ip)}`);
      return res.data;
    },
    staleTime: 1000 * 60 * 30, // cache 30min
  });
}