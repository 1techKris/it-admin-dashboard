// frontend/src/features/vpn/VPNSessions.tsx

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../../lib/api/client";
import { XCircle, LogOut } from "lucide-react";

export default function VPNSessions() {
  const queryClient = useQueryClient();

  const vpn = useQuery({
    queryKey: ["vpnSessions"],
    queryFn: async () => {
      try {
        const res = await api.get("/vpn/sessions");
        return res.data;
      } catch (err) {
        return { connected: [] };
      }
    },
    refetchInterval: 5000,
  });

  const data = vpn.data ?? {};
  const sessions = Array.isArray(data.connected) ? data.connected : [];

  // Format "Seconds" → "1h 22m"
  const formatDuration = (sec: number) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    return `${h}h ${m}m`;
  };

  // ===============================
  // DISCONNECT MUTATION
  // ===============================
  const disconnectMutation = useMutation({
    mutationFn: (username: string) =>
      api.post("/vpn/disconnect", { username }),
    onSuccess: () => {
      queryClient.invalidateQueries(["vpnSessions"]);
    },
  });

  const disconnectUser = (username: string) => {
    if (!window.confirm(`Disconnect ${username}?`)) return;

    disconnectMutation.mutate(username);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold dark:text-white">
        VPN Sessions
      </h1>

      <div className="card p-4 rounded-lg">

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-600 dark:text-slate-300 border-b border-slate-300 dark:border-slate-700">
              <th className="py-2">User</th>
              <th className="py-2">IP</th>
              <th className="py-2">Start Time</th>
              <th className="py-2">Duration</th>
              <th className="py-2 text-right">Actions</th>
            </tr>
          </thead>

          <tbody>
            {sessions.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="py-6 text-center dark:text-slate-400"
                >
                  No active VPN sessions.
                </td>
              </tr>
            )}

            {sessions.map((s: any, i: number) => (
              <tr
                key={i}
                className="border-b border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <td className="py-2">{s.Username}</td>
                <td className="py-2">{s.ClientIPv4Address}</td>

                <td className="py-2">
                  {new Date(s.ConnectionStartTime).toLocaleString()}
                </td>

                <td className="py-2">
                  {formatDuration(s.ConnectionDuration?.Seconds ?? 0)}
                </td>

                <td className="py-2 text-right">
                  <button
                    onClick={() => disconnectUser(s.Username)}
                    className="border px-3 py-1 rounded flex items-center gap-1 hover:bg-red-50 dark:hover:bg-red-900 dark:border-red-700 text-red-600 dark:text-red-400 ml-auto"
                  >
                    <LogOut size={14} />
                    Disconnect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>

        </table>

      </div>
    </div>
  );
}