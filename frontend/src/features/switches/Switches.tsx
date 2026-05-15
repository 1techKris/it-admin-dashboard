import { useEffect, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";
import { Link } from "react-router-dom";

export default function Switches() {
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const res = await api.get(endpoints.network.lastScanResults);
      const all = res.data.results || [];
      setDevices(all.filter((d: any) => d.device_class === "switch"));
    } catch (err) {
      console.error(err);
      alert("Failed to load switches");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <div className="p-4">Loading switches…</div>;

  return (
    <div className="grid gap-4 p-2">
      <h2 className="text-lg font-semibold">Switches</h2>

      <div className="border rounded-xl bg-white dark:bg-slate-800 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="p-2 text-left">IP</th>
              <th className="p-2 text-left">Vendor</th>
              <th className="p-2 text-left">Model</th>
              <th className="p-2 text-left">Hostname</th>
              <th className="p-2 text-left">Details</th>
            </tr>
          </thead>

          <tbody>
            {devices.map((d) => (
              <tr key={d.ip} className="border-t">
                <td className="p-2 font-mono">{d.ip}</td>
                <td className="p-2">{d.vendor || "Unknown"}</td>
                <td className="p-2">{d.model || "Unknown"}</td>
                <td className="p-2">{d.hostname || "Unknown"}</td>
                <td className="p-2">
                  <Link
                    to={`/devices/${d.ip}`}
                    className="px-2 py-1 border rounded bg-slate-100 hover:bg-slate-200"
                  >
                    Open
                  </Link>
                </td>
              </tr>
            ))}

            {!devices.length && (
              <tr>
                <td colSpan={5} className="p-3 text-slate-500">
                  No switches detected
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}