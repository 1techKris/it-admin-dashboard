// frontend/src/features/vpn/SettingsVPN.tsx

import { useQuery, useMutation } from "@tanstack/react-query";
import api from "../../lib/api/client";
import { useState, useEffect } from "react";

export default function SettingsVPN() {
  const { data: initial } = useQuery({
    queryKey: ["vpn-settings"],
    queryFn: async () => (await api.get("/settings/vpn")).data,
  });

  const [server, setServer] = useState("");
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (initial) {
      setServer(initial.vpn_server || "");
      setUser(initial.vpn_user || "");
      setPassword("");
    }
  }, [initial]);

  const save = useMutation({
    mutationFn: async () =>
      api.put("/settings/vpn", {
        vpn_server: server,
        vpn_user: user,
        vpn_password: password,
      }),
  });

  const test = useMutation({
    mutationFn: async () =>
      api.post("/settings/vpn/test", {
        vpn_server: server,
        vpn_user: user,
        vpn_password: password,
      }),
  });

  return (
    <div className="p-4 grid gap-4 max-w-xl">
      <h2 className="text-xl font-semibold">VPN Settings</h2>

      <div className="border rounded-xl p-4 bg-white dark:bg-slate-800 grid gap-4">

        <div>
          <label className="text-xs text-slate-500">VPN Server</label>
          <input
            className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            value={server}
            onChange={(e) => setServer(e.target.value)}
            placeholder="e.g. 192.168.1.10 or http://server:5985"
          />
        </div>

        <div>
          <label className="text-xs text-slate-500">Service Account</label>
          <input
            className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            value={user}
            onChange={(e) => setUser(e.target.value)}
            placeholder="DOMAIN\\username"
          />
        </div>

        <div>
          <label className="text-xs text-slate-500">Password</label>
          <input
            type="password"
            className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="New password (blank = unchanged)"
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => save.mutate()}
            className="px-4 py-2 rounded bg-blue-600 text-white"
          >
            {save.isLoading ? "Saving…" : "Save"}
          </button>

          <button
            onClick={() => test.mutate()}
            className="px-4 py-2 rounded bg-green-600 text-white"
          >
            {test.isLoading ? "Testing…" : "Test"}
          </button>
        </div>

        {test.data?.data?.ok && (
          <div className="text-green-600">
            ✓ VPN reachable — {test.data.data.sample} active sessions
          </div>
        )}
      </div>
    </div>
  );
}