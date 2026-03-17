import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";
import { useState } from "react";
import DeviceDetailModal from "./DeviceDetailModal";

type Device = {
  device_id: string;
  type: string;      // Server, Client, Network, Printer
  os: string;
  ip: string;
  cpu: number;
  mem: number;
  status: string;
  archived?: boolean;
  last_seen?: string | null;
  latency_ms?: number | null;
  custom_name?: string | null;
};

export default function Servers() {
  const qc = useQueryClient();
  const [showArchived, setShowArchived] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["servers", { showArchived }],
    queryFn: async () =>
      (await api.get<Device[]>(endpoints.servers.list("", "all", 1, showArchived))).data,
    refetchInterval: 5000,
  });

  const archive = useMutation({
    mutationFn: async (id: string) =>
      (await api.delete(endpoints.servers.archive(id))).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["servers"] }),
  });

  const restore = useMutation({
    mutationFn: async (id: string) =>
      (await api.post(endpoints.servers.restore(id))).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["servers"] }),
  });

  if (isLoading) return <div className="text-sm text-slate-500">Loading servers…</div>;
  if (isError) return <div className="text-sm text-red-600">Failed to load servers.</div>;

  // FILTER OUT PRINTERS
  const rows = (data || []).filter((d) => d.type.toLowerCase() !== "printer");

  return (
    <div className="grid gap-3">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">Servers</h2>

        <label className="text-xs flex items-center gap-2">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={() => setShowArchived(!showArchived)}
          />
          Show archived
        </label>
      </div>

      <div className="overflow-x-auto border rounded-xl bg-white dark:bg-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-700">
            <tr>
              <th className="p-2 text-left">ID</th>
              <th className="p-2 text-left">Type</th>
              <th className="p-2 text-left">OS</th>
              <th className="p-2 text-left">IP</th>
              <th className="p-2 text-left">Status</th>
              <th className="p-2 text-left">Latency</th>
              <th className="p-2 text-left">Last seen</th>
              <th className="p-2 text-left">Actions</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((d) => (
              <tr
                key={d.device_id}
                className="border-t hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer"
                onClick={() => setSelectedDevice(d)}
              >
                <td className="p-2">{d.custom_name || d.device_id}</td>
                <td className="p-2">{d.type}</td>
                <td className="p-2">{d.os}</td>
                <td className="p-2 font-mono text-xs">{d.ip}</td>
                <td className="p-2">
                  <span
                    className={`px-2 py-1 text-xs rounded border ${
                      d.status === "Healthy"
                        ? "bg-green-50 border-green-300 text-green-700"
                        : d.status === "Down"
                        ? "bg-red-50 border-red-300 text-red-700"
                        : "bg-slate-50 border-slate-300 text-slate-700"
                    }`}
                  >
                    {d.status}
                  </span>
                </td>
                <td className="p-2">
                  {d.latency_ms != null ? `${d.latency_ms} ms` : "—"}
                </td>
                <td className="p-2">
                  {d.last_seen ? new Date(d.last_seen).toLocaleString() : "—"}
                </td>
                <td className="p-2" onClick={(e) => e.stopPropagation()}>
                  {!d.archived ? (
                    <button
                      className="text-xs px-3 py-1 border rounded hover:bg-slate-50"
                      onClick={() => archive.mutate(d.device_id)}
                    >
                      Archive
                    </button>
                  ) : (
                    <button
                      className="text-xs px-3 py-1 border rounded hover:bg-slate-50"
                      onClick={() => restore.mutate(d.device_id)}
                    >
                      Restore
                    </button>
                  )}
                </td>
              </tr>
            ))}

            {!rows.length && (
              <tr>
                <td className="p-3 text-sm text-slate-500" colSpan={8}>
                  No servers found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <DeviceDetailModal
        device={selectedDevice}
        onClose={() => setSelectedDevice(null)}
      />
    </div>
  );
}