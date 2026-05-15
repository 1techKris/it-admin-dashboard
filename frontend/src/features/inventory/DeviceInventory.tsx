import { useEffect, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";
import { Link } from "react-router-dom";

type Device = {
  ip: string;
  device_class?: string;
  vendor?: string;
  model?: string;
  hostname?: string;
  os?: string;
};

export default function DeviceInventory() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const res = await api.get(endpoints.network.lastScanResults);
      setDevices(res.data.results || []);
    } catch (err) {
      console.error(err);
      alert("Failed to load device inventory");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const sorted = [...devices].sort((a, b) => {
    const ca = a.device_class || "Unknown";
    const cb = b.device_class || "Unknown";
    if (ca !== cb) return ca.localeCompare(cb);
    return a.ip.localeCompare(b.ip, undefined, { numeric: true });
  });

  const groups: Record<string, Device[]> = {};

  sorted.forEach((d) => {
    const key = d.device_class || "Unknown";
    if (!groups[key]) groups[key] = [];
    groups[key].push(d);
  });

  if (loading) {
    return <div className="p-4">Loading device inventory…</div>;
  }

  return (
    <div className="grid gap-6 p-2">
      <h2 className="text-lg font-semibold">Device Inventory</h2>

      {Object.entries(groups).map(([className, entries]) => (
        <div key={className} className="border rounded-2xl bg-white dark:bg-slate-800">
          <div className="px-4 py-2 text-sm font-semibold bg-slate-100 dark:bg-slate-700 rounded-t-2xl">
            {className} ({entries.length})
          </div>

          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700">
              <tr>
                <th className="p-2 text-left">IP</th>
                <th className="p-2 text-left">Vendor</th>
                <th className="p-2 text-left">Model</th>
                <th className="p-2 text-left">Hostname</th>
                <th className="p-2 text-left">OS</th>
                <th className="p-2 text-left">Details</th>
              </tr>
            </thead>

            <tbody>
              {entries.map((d) => (
                <tr key={d.ip} className="border-t">
                  <td className="p-2 font-mono">{d.ip}</td>
                  <td className="p-2">{d.vendor || "—"}</td>
                  <td className="p-2">{d.model || "—"}</td>
                  <td className="p-2">{d.hostname || "—"}</td>
                  <td className="p-2">{d.os || "Unknown"}</td>
                  <td className="p-2">
                    <Link
                      to={`/devices/${d.ip}`}
                      className="px-2 py-1 border rounded bg-slate-100 hover:bg-slate-200"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}