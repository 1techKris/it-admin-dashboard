import { useEffect, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";
import { useParams } from "react-router-dom";

type SwitchStatus = {
  vendor: string;
  model: string;
  sys_descr: string;
  sys_name: string;
};

type InterfaceItem = {
  index: number;
  name: string;
  admin_status: number;
  oper_status: number;
};

type LLDPItem = {
  local_port: string;
  remote_name: string;
  remote_port: string;
};

type CDPItem = {
  local_port: string;
  remote_name: string;
  remote_port: string;
};

type VlanMap = Record<string, string>;

type MacItem = {
  mac: string;
  port: number;
};

type FullSnapshot = {
  status: SwitchStatus;
  interfaces: InterfaceItem[];
  vlans: VlanMap;
  neighbors: {
    lldp: LLDPItem[];
    cdp: CDPItem[];
  };
  mac_table: MacItem[];
};

export default function SwitchDetails() {
  const { ip } = useParams();
  const [snap, setSnap] = useState<FullSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  async function load() {
    if (!ip) return;
    try {
      setLoading(true);
      const { data } = await api.get(endpoints.switch.all(ip));
      setSnap(data);
    } catch (err) {
      console.error(err);
      alert("Failed to load switch data.");
    } finally {
      setLoading(false);
    }
  }

  // Auto-refresh every 5 seconds when enabled
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [autoRefresh, ip]);

  useEffect(() => {
    load();
  }, [ip]);

  if (!ip) return <div className="p-4">Invalid switch IP.</div>;

  const status = snap?.status;
  const interfaces = snap?.interfaces || [];
  const vlans = snap?.vlans || {};
  const lldp = snap?.neighbors?.lldp || [];
  const cdp = snap?.neighbors?.cdp || [];
  const mac = snap?.mac_table || [];

  return (
    <div className="grid gap-6">
      <h2 className="text-lg font-semibold">
        Switch Details: <span className="font-mono">{ip}</span>
      </h2>

      {/* Controls */}
      <div className="flex gap-3 items-center">
        <button
          onClick={load}
          disabled={loading}
          className="px-4 py-2 border rounded bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-100"
        >
          {loading ? "Loading…" : "Refresh"}
        </button>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          <span className="text-sm text-slate-600 dark:text-slate-300">
            Auto-refresh (5s)
          </span>
        </label>
      </div>

      {/* BASIC INFO */}
      <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800 shadow">
        <h3 className="font-semibold mb-3">Basic Info</h3>
        <div className="grid md:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-slate-500">Vendor</div>
            <div>{status?.vendor || "Unknown"}</div>
          </div>
          <div>
            <div className="text-slate-500">Model</div>
            <div>{status?.model || "Unknown"}</div>
          </div>
          <div>
            <div className="text-slate-500">System Name</div>
            <div>{status?.sys_name || "Unknown"}</div>
          </div>
          <div>
            <div className="text-slate-500">System Description</div>
            <div className="text-xs break-all">{status?.sys_descr}</div>
          </div>
        </div>
      </div>

      {/* INTERFACES */}
      <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800 shadow">
        <h3 className="font-semibold mb-3">Interfaces</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700">
              <tr>
                <th className="p-2 text-left">Index</th>
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Admin</th>
                <th className="p-2 text-left">Oper</th>
              </tr>
            </thead>
            <tbody>
              {interfaces.map((i) => (
                <tr key={i.index} className="border-t">
                  <td className="p-2 font-mono">{i.index}</td>
                  <td className="p-2">{i.name}</td>
                  <td className="p-2">
                    {i.admin_status === 1 ? (
                      <span className="text-green-700">Up</span>
                    ) : (
                      <span className="text-red-700">Down</span>
                    )}
                  </td>
                  <td className="p-2">
                    {i.oper_status === 1 ? (
                      <span className="text-green-700">Up</span>
                    ) : (
                      <span className="text-red-700">Down</span>
                    )}
                  </td>
                </tr>
              ))}

              {!interfaces.length && (
                <tr>
                  <td colSpan={4} className="p-2 text-slate-500">
                    No interfaces reported.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* VLANs */}
      <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800 shadow">
        <h3 className="font-semibold mb-3">VLANs</h3>
        {Object.keys(vlans).length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700">
              <tr>
                <th className="p-2 text-left">VLAN ID</th>
                <th className="p-2 text-left">Name</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(vlans).map(([id, name]) => (
                <tr key={id} className="border-t">
                  <td className="p-2">{id}</td>
                  <td className="p-2">{name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-slate-500 text-sm">No VLANs reported.</div>
        )}
      </div>

      {/* NEIGHBORS */}
      <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800 shadow">
        <h3 className="font-semibold mb-3">Neighbors</h3>

        {/* LLDP */}
        <h4 className="font-semibold mb-1">LLDP</h4>
        {lldp.length > 0 ? (
          <table className="w-full text-sm mb-4">
            <thead className="bg-slate-50 dark:bg-slate-700">
              <tr>
                <th className="p-2 text-left">Local Port</th>
                <th className="p-2 text-left">Remote Name</th>
                <th className="p-2 text-left">Remote Port</th>
              </tr>
            </thead>
            <tbody>
              {lldp.map((n, idx) => (
                <tr key={idx} className="border-t">
                  <td className="p-2">{n.local_port}</td>
                  <td className="p-2">{n.remote_name}</td>
                  <td className="p-2">{n.remote_port}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-slate-500 text-sm mb-4">No LLDP neighbors.</div>
        )}

        {/* CDP */}
        <h4 className="font-semibold mb-1">CDP</h4>
        {cdp.length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700">
              <tr>
                <th className="p-2 text-left">Local Port</th>
                <th className="p-2 text-left">Remote Name</th>
                <th className="p-2 text-left">Remote Port</th>
              </tr>
            </thead>
            <tbody>
              {cdp.map((n, idx) => (
                <tr key={idx} className="border-t">
                  <td className="p-2">{n.local_port}</td>
                  <td className="p-2">{n.remote_name}</td>
                  <td className="p-2">{n.remote_port}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-slate-500 text-sm">No CDP neighbors.</div>
        )}
      </div>

      {/* MAC TABLE */}
      <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800 shadow">
        <h3 className="font-semibold mb-3">MAC Table</h3>
        {mac.length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700">
              <tr>
                <th className="p-2 text-left">MAC Address</th>
                <th className="p-2 text-left">Port</th>
              </tr>
            </thead>
            <tbody>
              {mac.map((row, idx) => (
                <tr key={idx} className="border-t">
                  <td className="p-2 font-mono">{row.mac}</td>
                  <td className="p-2">{row.port}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-slate-500 text-sm">No entries.</div>
        )}
      </div>
    </div>
  );
}