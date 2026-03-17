import { useEffect, useRef, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";

type ScanResult = {
  ip: string;
  alive: boolean;
  hostname?: string | null;
  open_ports: number[];
  banners?: Record<string, string> | Record<number, string>;
  os?: string;
  labels?: string[];
};

type ScanStatus = {
  id: string;
  cidr: string;
  status: "running" | "finished" | "error";
  total: number;
  completed: number;
  error?: string | null;
  results: ScanResult[];
};

export default function NetworkScan() {
  const [cidr, setCidr] = useState("192.168.125.0/24");
  const [ports, setPorts] = useState("22,80,443,3389,445,9100");
  const [status, setStatus] = useState<ScanStatus>({
    id: "",
    cidr: "",
    status: "running",
    total: 0,
    completed: 0,
    error: null,
    results: [],
  });

  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const wsRef = useRef<WebSocket | null>(null);

  function parsePorts(input: string): number[] {
    return input
      .split(",")
      .map((x) => parseInt(x.trim(), 10))
      .filter((n) => Number.isFinite(n) && n > 0 && n < 65536);
  }

  function buildWsUrl(scanId: string) {
    const apiBase =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
    const u = new URL(apiBase);
    const proto = u.protocol === "https:" ? "wss" : "ws";
    const wsPath =
      u.pathname.replace(/\/$/, "") + endpoints.network.wsScanPath(scanId);
    return `${proto}://${u.host}${wsPath}`;
  }

  async function startScan() {
    try {
      const body = { cidr, ports: parsePorts(ports) };
      const { data } = await api.post(endpoints.network.start, body);

      setStatus({
        id: data.id,
        cidr,
        status: "running",
        total: data.total || 0,
        completed: 0,
        error: null,
        results: [],
      });
      setSelected({});

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      const wsUrl = buildWsUrl(data.id);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        const payload = JSON.parse(ev.data);
        setStatus({ ...payload });
      };

      ws.onerror = (err) => console.error("WS error:", err);
      ws.onclose = () => console.log("WS closed");
    } catch (err) {
      console.error("Scan error:", err);
      alert("Scan failed — check backend logs.");
    }
  }

  async function importSelected() {
    if (!status.id) {
      alert("No active scan to import from.");
      return;
    }
    const ips = Object.keys(selected).filter((k) => selected[k]);
    const body = ips.length ? { ips } : {}; // empty -> backend imports all alive
    try {
      const res = await api.post(endpoints.network.import(status.id), body);
      alert(`Imported: ${res.data.created}, Skipped: ${res.data.skipped}`);
    } catch (e) {
      console.error(e);
      alert("Import failed. Check backend logs.");
    }
  }

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  const progress =
    status.total > 0
      ? Math.floor((status.completed / status.total) * 100)
      : 0;

  const hasResults = Array.isArray(status.results) && status.results.length > 0;

  return (
    <div className="grid gap-4">
      <h2 className="text-lg font-semibold">Network Scanner</h2>

      {/* Controls */}
      <div className="grid gap-2 border rounded-2xl p-4 bg-white dark:bg-slate-800">
        <div className="grid md:grid-cols-4 gap-3">
          {/* CIDR */}
          <div>
            <label className="text-xs text-slate-500">CIDR</label>
            <input
              className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
              value={cidr}
              onChange={(e) => setCidr(e.target.value)}
              placeholder="192.168.125.0/24"
            />
          </div>

          {/* Ports */}
          <div>
            <label className="text-xs text-slate-500">Ports</label>
            <input
              className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
              value={ports}
              onChange={(e) => setPorts(e.target.value)}
              placeholder="22,80,443,3389,445,9100"
            />
          </div>

          <div className="flex items-end gap-2">
            <button
              onClick={startScan}
              className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700 dark:border-slate-600"
            >
              Start Scan
            </button>
            <button
              onClick={importSelected}
              disabled={!hasResults}
              className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700 dark:border-slate-600"
              title="Import selected (or all alive if none selected) to Devices"
            >
              Import to Devices
            </button>
          </div>

          {/* Progress */}
          <div className="self-end">
            <div className="text-xs text-slate-500 dark:text-slate-300 mb-1">
              Status: {status.status} • {status.completed}/{status.total} ({progress}%)
              {status.error ? ` • Error: ${status.error}` : ""}
            </div>
            <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded">
              <div
                className="h-2 bg-blue-500 rounded"
                style={{ width: `${progress}%`, transition: "width .3s ease" }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* RESULTS TABLE */}
      <div className="overflow-x-auto border rounded-2xl bg-white dark:bg-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-700">
            <tr>
              <th className="p-2 text-left">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    const v = e.target.checked;
                    if (!hasResults) return;
                    const next: Record<string, boolean> = {};
                    status.results.forEach((r) => (next[r.ip] = v));
                    setSelected(next);
                  }}
                />
              </th>
              <th className="p-2 text-left">IP</th>
              <th className="p-2 text-left">Hostname</th>
              <th className="p-2 text-left">OS</th>
              <th className="p-2 text-left">Alive</th>
              <th className="p-2 text-left">Open Ports</th>
            </tr>
          </thead>

        <tbody>
          {hasResults ? (
            status.results
              .sort((a, b) => {
                const pa = a.ip.split(".").map(Number);
                const pb = b.ip.split(".").map(Number);
                for (let i = 0; i < 4; i++) {
                  if (pa[i] !== pb[i]) return pa[i] - pb[i];
                }
                return 0;
              })
              .map((r) => {
                const checked = !!selected[r.ip];
                const banners = r.banners || {};
                return (
                  <tr key={r.ip} className="border-t hover:bg-slate-50 dark:hover:bg-slate-700">
                    {/* Select */}
                    <td className="p-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) =>
                          setSelected((prev) => ({ ...prev, [r.ip]: e.target.checked }))
                        }
                        title="Select to import"
                      />
                    </td>

                    {/* IP */}
                    <td className="p-2 font-mono text-xs">{r.ip}</td>

                    {/* Hostname */}
                    <td className="p-2">
                      {r.hostname ? (
                        <span className="font-mono text-xs">{r.hostname}</span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>

                    {/* OS */}
                    <td className="p-2">{r.os || "Unknown"}</td>

                    {/* Alive */}
                    <td className="p-2">
                      <span
                        className={`px-2 py-1 text-xs rounded border ${
                          r.alive
                            ? "bg-green-50 border-green-300 text-green-700"
                            : "bg-slate-50 border-slate-300 text-slate-600"
                        }`}
                      >
                        {r.alive ? "Yes" : "No"}
                      </span>
                    </td>

                    {/* Ports + labels + banners (tooltip) */}
                    <td className="p-2">
                      {r.open_ports.length ? (
                        <div className="flex flex-wrap gap-1">
                          {r.open_ports.map((p) => {
                            const label =
                              (Array.isArray(r.labels) && r.labels[r.open_ports.indexOf(p)]) ||
                              `Port ${p}`;
                            const banner =
                              (banners as any)[p] ||
                              (banners as any)[String(p)] ||
                              "";
                            return (
                              <span
                                key={`${r.ip}-${p}`}
                                className="px-2 py-0.5 rounded text-xs border bg-blue-50 border-blue-300 text-blue-700"
                                title={banner || label}
                              >
                                {label}
                              </span>
                            );
                          })}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-500">—</span>
                      )}
                    </td>
                  </tr>
                );
              })
          ) : (
            <tr>
              <td colSpan={6} className="p-3 text-sm text-slate-500">
                No results yet or scan in progress...
              </td>
            </tr>
          )}
        </tbody>
        </table>
      </div>
    </div>
  );
}
