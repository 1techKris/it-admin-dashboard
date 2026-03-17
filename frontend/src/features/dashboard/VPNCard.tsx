// frontend/src/features/vpn/VPNCard.tsx

import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";

export default function VPNCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["vpn-sessions"],
    queryFn: async () => (await api.get("/vpn/sessions")).data,
    refetchInterval: 5000,
  });

  const count = data?.connected?.length ?? 0;

  return (
    <div className="border rounded-xl p-4 bg-white dark:bg-slate-800 shadow text-center">
      <h3 className="font-semibold text-lg">VPN Sessions</h3>

      {isLoading ? (
        <div className="mt-3 text-slate-500">Loading…</div>
      ) : (
        <div className="mt-3 text-4xl font-bold">{count}</div>
      )}

      <div className="text-xs text-slate-500 mt-1">Active VPN Users</div>
    </div>
  );
}