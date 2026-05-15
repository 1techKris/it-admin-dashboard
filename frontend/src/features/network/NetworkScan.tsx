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
  updated_at?: number | null;
  vendor?: string | null;
};

type ScanStatus = {
  id: string;
  cidr: string;
  status: "running" | "finished" | "error" | "cancelled";
  total: number;
  completed: number;
  error?: string | null;
  results: ScanResult[];
};

export default function NetworkScan() {
  const [cidr, setCidr] = useState("192.168.125.0/24");
  const [ports, setPorts] = useState("22,80,443,3389,445,9100");

  //
  // SCAN SPEED PROFILES
  //
  const [speed, setSpeed] = useState("normal");
  const speedProfiles = {
    slow: { concurrency: 8, host_delay: 0.1 },
    normal: { concurrency: 16, host_delay: 0.05 },
    fast: { concurrency: 32, host_delay: 0.01 },
    insane: { concurrency: 64, host_delay: 0 },
  };

  //
  // NEW: TIMEOUT CONTROLS
  //
  const [timeouts, setTimeouts] = useState({
    ping: 0.5,
    port: 1.0,
    snmp: 1.5,
    banner: 1.0,
    rdns: 0.7,
    netbios: 1.0,
  });

  //
  // Other UI States
  //
  const [aliveOnly, setAliveOnly] = useState(false);
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const [status, setStatus] = useState<ScanStatus>({
    id: "",
    cidr: "",
    status: "running",
    total: 0,
    completed: 0,
    error: null,
    results: [],
  });

  const wsRef = useRef<WebSocket | null>(null);
  const resultsRef = useRef<HTMLDivElement | null>(null);

  function parsePorts(s: string): number[] {
    return s
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

  //
  // Icons
  //
  function deviceIcon(os?: string, vendor?: string) {
    const o = os?.toLowerCase() || "";
    const v = vendor?.toLowerCase() || "";

    if (o.includes("windows")) return "🪟";
    if (o.includes("linux")) return "🐧";
    if (o.includes("printer") || v.includes("printer")) return "🖨️";
    if (v.includes("hp") || v.includes("hewlett")) return "🖨️";
    if (v.includes("ubiquiti")) return "📶";
    if (v.includes("cisco")) return "🔵";
    if (v.includes("mikrotik")) return "📡";

    return "🖥️";
  }

  function portColor(p: number) {
    if (p === 22) return "bg-green-100 border-green-300 text-green-700";
    if (p === 80 || p === 443)
      return "bg-blue-100 border-blue-300 text-blue-700";
    if (p === 3389)
      return "bg-purple-100 border-purple-300 text-purple-700";
    if (p === 445)
      return "bg-rose-100 border-rose-300 text-rose-700";
    if (p === 9100)
      return "bg-yellow-100 border-yellow-300 text-yellow-700";
    return "bg-slate-100 border-slate-300 text-slate-700";
  }

  //
  // START SCAN
  //
  async function startScan() {
    try {
      const parsedPorts = parsePorts(ports);
      const { concurrency, host_delay } = speedProfiles[speed];

      const body = {
        cidr,
        ports: parsedPorts,
        concurrency,
        host_delay,
        timeouts, // NEW
      };

      const { data } = await api.post(endpoints.network.start, body);

      setStatus({
        id: data.id,
        cidr,
        status: "running",
        total: data.total ?? 0,
        completed: 0,
        error: null,
        results: [],
      });

      setSelected({});
      setAliveOnly(false);

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      const ws = new WebSocket(buildWsUrl(data.id));
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

  //
  // STOP SCAN
  //
  async function stopScan() {
    if (!status.id) return;
    try {
      await api.post(endpoints.network.stop(status.id));
    } catch {
      alert("Failed to stop scan.");
    }
  }

  //
  // IMPORT SELECTED DEVICES
  //
  async function importSelected() {
    if (!status.id) {
      alert("No active scan.");
      return;
    }
    const ips = Object.keys(selected).filter((k) => selected[k]);
    const body = ips.length ? { ips } : {};
    try {
      const res = await api.post(endpoints.network.import(status.id), body);
      alert(`Imported: ${res.data.created}, Skipped: ${res.data.skipped}`);
    } catch {
      alert("Import failed.");
    }
  }

  //
  // AUTO-SCROLL RESULTS
  //
  useEffect(() => {
    if (resultsRef.current) {
      resultsRef.current.scrollTop = resultsRef.current.scrollHeight;
    }
  }, [status.results]);

  //
  // WS CLEANUP
  //
  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  const progress =
    status.total > 0
      ? Math.floor((status.completed / status.total) * 100)
      : 0;

  let displayedResults = status.results;
  if (aliveOnly) displayedResults = displayedResults.filter((r) => r.alive);

  const hasResults = displayedResults.length > 0;

  return (
    <div className="grid gap-4">
      <h2 className="text-lg font-semibold">Network Scanner</h2>

      {/* CONTROLS */}
      <div className="grid gap-2 border rounded-2xl p-4 bg-white dark:bg-slate-800">

        <div className="grid md:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-slate-500">CIDR</label>
            <input
              className="w-full border rounded px-3 py-2"
              value={cidr}
              onChange={(e) => setCidr(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs text-slate-500">Ports</label>
            <input
              className="w-full border rounded px-3 py-2"
              value={ports}
              onChange={(e) => setPorts(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs text-slate-500">Scan Speed</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={speed}
              onChange={(e) => setSpeed(e.target.value)}
            >
              <option value="slow">Slow</option>
              <option value="normal">Normal</option>
              <option value="fast">Fast</option>
              <option value="insane">Insane</option>
            </select>
          </div>

          <div className="flex items-end gap-2">
            <button onClick={startScan} className="px-3 py-2 border rounded">
              Start Scan
            </button>

            <button
              onClick={stopScan}
              disabled={!status.id || status.status !== "running"}
              className="px-3 py-2 border rounded bg-red-100 text-red-700"
            >
              Stop Scan
            </button>

            <button
              onClick={importSelected}
              disabled={!hasResults}
              className="px-3 py-2 border rounded"
            >
              Import
            </button>
          </div>
        </div>

        {/* ALIVE FILTER */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={aliveOnly}
            onChange={(e) => setAliveOnly(e.target.checked)}
          />
          <span className="text-xs text-slate-600">Show Alive Only</span>
        </div>

        {/* NEW TIMEOUT UI */}
        <div>
          <h3 className="font-semibold text-sm mb-2">Timeouts (seconds)</h3>

          <div className="grid md:grid-cols-3 gap-3">
            {Object.entries(timeouts).map(([key, val]) => (
              <div key={key}>
                <label className="text-xs capitalize">
                  {key} timeout
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="w-full border rounded px-3 py-2"
                  value={val}
                  onChange={(e) =>
                    setTimeouts((t) => ({
                      ...t,
                      [key]:
                        e.target.value === "" ? 0 : parseFloat(e.target.value),
                    }))
                  }
                />
              </div>
            ))}
          </div>
        </div>

        {/* PROGRESS BAR */}
        <div>
          <div className="text-xs mb-1">
            Status: {status.status} • {status.completed}/{status.total} (
            {progress}%)
          </div>
          <div className="w-full h-2 bg-slate-200 rounded">
            <div
              className="h-2 bg-blue-500 rounded"
              style={{ width: `${progress}%`, transition: "width 0.3s" }}
            ></div>
          </div>
        </div>
      </div>

      {/* RESULTS */}
      <div
        ref={resultsRef}
        className="overflow-y-auto max-h-[600px] border rounded-2xl bg-white dark:bg-slate-800"
      >
        <table className="w-full text-sm">
<thead className="bg-slate-50">
  <tr>
    <th className="p-2">
      <input
        type="checkbox"
        onChange={(e) => {
          const v = e.target.checked;
          const next: Record<string, boolean> = {};
          displayedResults.forEach((r) => (next[r.ip] = v));
          setSelected(next);
        }}
      />
    </th>
    <th className="p-2">IP</th>
    <th className="p-2">Class</th>
    <th className="p-2">Vendor</th>
    <th className="p-2">Model</th>
    <th className="p-2">Hostname</th>
    <th className="p-2">OS</th>
    <th className="p-2">Alive</th>
    <th className="p-2">Ports</th>
  </tr>
</thead>

<tbody>
  {!hasResults && (
    <tr>
      <td colSpan={9} className="p-3 text-slate-500">
        No results yet…
      </td>
    </tr>
  )}

  {hasResults &&
    displayedResults
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
        const flash =
          r.updated_at && Date.now() / 1000 - r.updated_at < 0.5;

        const banners = r.banners || {};

        return (
          <tr
            key={r.ip}
            className={`border-t ${
              flash ? "bg-yellow-100 animate-pulse" : ""
            }`}
          >
            <td className="p-2">
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) =>
                  setSelected((prev) => ({
                    ...prev,
                    [r.ip]: e.target.checked,
                  }))
                }
              />
            </td>

            <td className="p-2 font-mono text-xs">{r.ip}</td>
            <td className="p-2">{r.device_class || "Unknown"}</td>
            <td className="p-2">{r.vendor || "—"}</td>
            <td className="p-2">{r.model || "—"}</td>
            <td className="p-2">
              {r.hostname || <span className="text-slate-400">—</span>}
            </td>
            <td className="p-2">{r.os || "Unknown"}</td>

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

            <td className="p-2">
              {r.open_ports.length ? (
                <div className="flex flex-wrap gap-1">
                  {r.open_ports.map((p, idx) => {
                    const labels = r.labels || [];
                    const label = labels[idx] || `Port ${p}`;
                    const banner =
                      (banners as any)[p] ||
                      (banners as any)[String(p)] ||
                      "";

                    return (
                      <span
                        key={`${r.ip}-${p}`}
                        className={`px-2 py-0.5 rounded text-xs border`}
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
      })}
</tbody>
        </table>
      </div>
    </div>
  );
}