// frontend/src/features/vpn/VPNAlerts.tsx

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../../lib/api/client";
import React, { useState } from "react";

export default function VPNAlerts() {
  const qc = useQueryClient();
  const [username, setUsername] = useState("");

  const { data } = useQuery({
    queryKey: ["vpn-alert-rules"],
    queryFn: async () => (await api.get("/vpn/alerts/rules")).data,
  });

  const addRule = useMutation({
    mutationFn: async () =>
      (await api.post("/vpn/alerts/rules/add?username=" + username)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vpn-alert-rules"] });
      setUsername("");
    },
  });

  const removeRule = useMutation({
    mutationFn: async (u: string) =>
      (await api.post("/vpn/alerts/rules/remove?username=" + u)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vpn-alert-rules"] });
    },
  });

  return (
    <div className="p-4 grid gap-4 max-w-md">
      <h2 className="text-xl font-semibold">VPN Alerts</h2>

      <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
        <h3 className="font-semibold mb-2">Watchlist Users</h3>

        <div className="grid gap-2">
          {data?.map((r: any) => (
            <div
              key={r.id}
              className="flex items-center justify-between border rounded px-3 py-1"
            >
              <span>{r.username}</span>
              <button
                onClick={() => removeRule.mutate(r.username)}
                className="px-2 py-1 bg-red-600 text-white text-xs rounded"
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <div className="mt-4 flex gap-2">
          <input
            className="border flex-1 rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            placeholder="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <button
            onClick={() => addRule.mutate()}
            className="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  );
}