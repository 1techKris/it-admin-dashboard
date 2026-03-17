import { useEffect, useRef, useState } from "react";
import api from "../../lib/api/client";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
} from "recharts";

type Telemetry = {
  cpu: number;
  mem: number;
  latency: number | null;
  alive: boolean;
  t: number;
};

export default function DeviceDetailModal({
  device,
  onClose,
}: {
  device: any;
  onClose: () => void;
}) {
  const [telemetry, setTelemetry] = useState<Telemetry[]>([]);
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({
    os: device?.os || "",
    custom_name: device?.custom_name || "",
    type: device?.type || "",
    status: device?.status || "",
  });

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!device) return;

    // reset edit form when device changes
    setForm({
      os: device.os || "",
      custom_name: device.custom_name || "",
      type: device.type || "",
      status: device.status || "",
    });

    const base =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
    const u = new URL(base);
    const proto = u.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${proto}://${u.host}${u.pathname.replace(
      /\/$/,
      ""
    )}/devices/ws/${device.device_id}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      setTelemetry((prev) => [...prev.slice(-40), data]); // last 40 samples
    };

    ws.onerror = (err) => console.error("Telemetry WS error:", err);
    ws.onclose = () => console.log("Telemetry WS closed");

    return () => wsRef.current?.close();
  }, [device]);

  function upd(field: string, val: string) {
    setForm((prev) => ({ ...prev, [field]: val }));
  }

  async function saveEdits() {
    if (!device) return;
    try {
      await api.post(`/servers/${device.device_id}/edit`, form);
      // Apply changes locally so the modal reflects immediately
      device.os = form.os;
      device.custom_name = form.custom_name;
      device.type = form.type;
      device.status = form.status;
      setEditMode(false);
      alert("Saved");
    } catch (err) {
      console.error(err);
      alert("Failed to save changes. Check backend logs.");
    }
  }

  async function action(path: string) {
    try {
      await api.post(path);
      alert("Action sent.");
    } catch (err) {
      console.error(err);
      alert("Action failed. Check backend logs.");
    }
  }

  if (!device) return null;

  const displayName = device.custom_name || device.device_id;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-3xl p-6 relative">

        {/* CLOSE */}
        <button
          onClick={onClose}
          className="absolute top-2 right-2 text-slate-500 hover:text-slate-700"
        >
          ✕
        </button>

        <h2 className="text-xl font-semibold mb-4">{displayName}</h2>

        {/* DEVICE INFO */}
        <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
          <div>
            <strong>Type:</strong> {device.type}
            <div><strong>OS:</strong> {device.os}</div>
            <div><strong>IP:</strong> {device.ip}</div>
            <div><strong>Status:</strong> {device.status}</div>
          </div>
          <div>
            <div><strong>Last Seen:</strong> {device.last_seen || "—"}</div>
            <div><strong>Latency:</strong> {device.latency_ms ?? "—"} ms</div>
            <div><strong>CPU:</strong> {device.cpu}%</div>
            <div><strong>MEM:</strong> {device.mem}%</div>
          </div>
        </div>

        {/* EDIT TOGGLE / FORM */}
        <div className="mb-4">
          {!editMode ? (
            <button
              onClick={() => setEditMode(true)}
              className="px-3 py-2 border rounded hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              Edit Device
            </button>
          ) : (
            <div className="p-3 border rounded-xl bg-slate-50 dark:bg-slate-700 mt-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-500">Custom Name</label>
                  <input
                    className="w-full p-2 border rounded dark:bg-slate-800"
                    value={form.custom_name}
                    onChange={(e) => upd("custom_name", e.target.value)}
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-500">OS</label>
                  <input
                    className="w-full p-2 border rounded dark:bg-slate-800"
                    value={form.os}
                    onChange={(e) => upd("os", e.target.value)}
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-500">Type</label>
                  <input
                    className="w-full p-2 border rounded dark:bg-slate-800"
                    value={form.type}
                    onChange={(e) => upd("type", e.target.value)}
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-500">Status</label>
                  <input
                    className="w-full p-2 border rounded dark:bg-slate-800"
                    value={form.status}
                    onChange={(e) => upd("status", e.target.value)}
                  />
                </div>
              </div>

              <div className="flex gap-2 mt-3">
                <button
                  onClick={saveEdits}
                  className="px-3 py-2 border rounded bg-blue-500 text-white hover:bg-blue-600"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditMode(false)}
                  className="px-3 py-2 border rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ACTION BUTTONS */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => action(`/servers/${device.device_id}/actions/reboot`)}
            className="px-3 py-2 border rounded hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            Reboot
          </button>

          <button
            onClick={() =>
              action(`/servers/${device.device_id}/actions/shutdown`)
            }
            className="px-3 py-2 border rounded hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            Shutdown
          </button>

          {String(device.os || "").toLowerCase().includes("windows") && (
            <button
              onClick={() => (window.location.href = `rdp://${device.ip}`)}
              className="px-3 py-2 border rounded hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              RDP
            </button>
          )}

          {!String(device.os || "").toLowerCase().includes("windows") && (
            <button
              onClick={() => (window.location.href = `ssh://${device.ip}`)}
              className="px-3 py-2 border rounded hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              SSH
            </button>
          )}

          <button
            onClick={() =>
              action(`/servers/${device.device_id}/actions/run-update`)
            }
            className="px-3 py-2 border rounded hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            Run Updates
          </button>
        </div>

        {/* MINI CHART */}
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={telemetry}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="t" />
              <YAxis />
              <Tooltip />

              <Area
                type="monotone"
                dataKey="cpu"
                stroke="#3b82f6"
                fill="#3b82f680"
                name="CPU"
              />
              <Area
                type="monotone"
                dataKey="mem"
                stroke="#22c55e"
                fill="#22c55e80"
                name="Memory"
              />
              <Area
                type="monotone"
                dataKey="latency"
                stroke="#f59e0b"
                fill="#f59e0b80"
                name="Latency (ms)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}