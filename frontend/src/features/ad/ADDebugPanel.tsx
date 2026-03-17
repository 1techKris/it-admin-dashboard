// frontend/src/features/ad/ADDebugPanel.tsx

import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";

export default function ADDebugPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["ad-debug"],
    queryFn: async () => (await api.get("/ad/debug")).data, // baseURL should be /api/v1
    refetchInterval: 5000,
  });

  if (isLoading) return <div className="text-sm text-slate-500">Loading AD diagnostics…</div>;
  if (isError) return <div className="text-sm text-red-600">Failed to load AD debug data.</div>;

  const d = data;

  return (
    <div className="border rounded-xl p-4 bg-white dark:bg-slate-800 grid gap-2 text-sm">
      <h3 className="font-semibold text-lg mb-2">AD Debug Panel</h3>
      <div><b>Input Server:</b> {d.input_server}</div>
      <div><b>Normalized Server:</b> {d.clean_server}</div>
      <div><b>DNS Resolution:</b> {d.server_dns}</div>
      <div><b>Reachable:</b> {d.server_reachable ? "Yes" : "No"}</div>
      <div><b>Bind OK:</b> {d.bind_ok ? "Yes" : "No"}</div>
      {!d.bind_ok && <div className="text-red-600"><b>Error:</b> {d.bind_error}</div>}
      <div><b>Latency:</b> {d.latency_ms != null ? `${d.latency_ms} ms` : "—"}</div>
      <div><b>Sample user count:</b> {d.sample_user_count ?? "—"}</div>
      <div><b>Base DN:</b> {d.base_dn}</div>
      <div><b>User:</b> {d.user}</div>
      <div><b>SSL:</b> {d.use_ssl ? "Yes" : "No"}</div>
    </div>
  );
}