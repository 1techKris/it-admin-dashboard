import { useEffect, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";

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
  const [ip, setIp] = useState("192.168.125.10");
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const [snap, setSnap] = useState<FullSnapshot | null>(null);

  async function load() {
    try {
      setLoading(true);
      const { data } = await api.get(endpoints.switch.all(ip));
      setSnap(data);
    } catch (err) {
      console.error(err);
      alert("Failed to load switch data. Check backend.");
    } finally {
      setLoading(false);
    }
  }

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => load(), 5000);
    return () => clearInterval(id);
  }, [autoRefresh, ip]);

  const status = snap?.status;
  const interfaces = snap?.interfaces || [];
  const vlans = snap?.vlans || {};
  const lldp = snap?.neighbors?.lldp || [];
  const cdp = snap?.neighbors?.cdp || [];
  const mac = snap?.mac_table || [];

  return (
    <div className="grid gap-4">
      <h2 className="text-lg font-semibold">Switch Details</h2>

      {/* Controls */}
      <div className="grid gap-2 border rounded-2xl p-4 bg-white dark:bg-slate-800">
        <div className="flex gap-3 items-end">
          <div className="flex flex-col">
            <label className="text-xs text-slate-500">Switch IP</label>
            <input
              className="border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
              value={ip}
              onChange={(e) => setIp(e.target.value)}
            />
          </div>

          <button
            onClick={load}
            disabled={loading}
            className="px-4 py-2 border rounded bg-blue-100 text-blue-700 dark:bg-blue-900 dark:border-blue-700"
          >
            {loading ? "Loading…" : "Load"}
          </button>

          <label className="flex items-center gap-2 text-sm ml-4">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (5s)
          </label>
        </div>
      </div>

      {!snap && (
        <div className="text-sm text-slate-500">
          Enter a switch IP and click <strong>Load</strong>.
        </div>
      )}

      {snap && (
        <div className="grid gap-6">
          {/* SWITCH BASIC INFO */}
          <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800">
            <h3 className="font-semibold mb-2">Basic Info</h3>
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
          <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800">
            <h3 className="font-semibold mb-2">Interfaces</h3>
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
                  {interfaces.map((intf) => (
                    <tr key={intf.index} className="border-t">
                      <td className="p-2 font-mono">{intf.index}</td>
                      <td className="p-2">{intf.name}</td>
                      <td className="p-2">
                        {intf.admin_status === 1 ? (
                          <span className="text-green-700">Up</span>
                        ) : (
                          <span className="text-red-700">Down</span>
                        )}
                      </td>
                      <td className="p-2">
                        {intf.oper_status === 1 ? (
                          <span className="text-green-700">Up</span>
                        ) : (
                          <span className="text-red-700">Down</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!interfaces.length && (
                    <tr>
                      <td colSpan={4} className="text-slate-500 p-3">
                        No interfaces reported.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* VLANs */}
          <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800">
            <h3 className="font-semibold mb-2">VLANs</h3>
            {Object.keys(vlans).length ? (
              <table className="text-sm w-full">
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
          <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800">
            <h3 className="font-semibold mb-2">Neighbors</h3>
            <div className="grid gap-6 md:grid-cols-2">
              {/* LLDP */}
              <div>
                <h4 className="font-semibold">LLDP</h4>
                {lldp.length ? (
                  <table className="text-sm w-full mt-2">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="p-2">Local Port</th>
                        <th className="p-2">Remote Name</th>
                        <th className="p-2">Remote Port</th>
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
                  <div className="text-slate-500 text-sm">No LLDP neighbors.</div>
                )}
              </div>

              {/* CDP */}
              <div>
                <h4 className="font-semibold">CDP</h4>
                {cdp.length ? (
                  <table className="text-sm w-full mt-2">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="p-2">Local Port</th>
                        <th className="p-2">Remote Name</th>
                        <th className="p-2">Remote Port</th>
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
            </div>
          </div>

          {/* MAC TABLE */}
          <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800">
            <h3 className="font-semibold mb-2">MAC Table</h3>
            {mac.length ? (
              <table className="text-sm w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="p-2">MAC</th>
                    <th className="p-2">Port</th>
                  </tr>
                </thead>
                <tbody>
                  {mac.map((m, idx) => (
                    <tr key={idx} className="border-t">
                      <td className="p-2 font-mono">{m.mac}</td>
                      <td className="p-2">{m.port}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-slate-500 text-sm">No MAC entries.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}