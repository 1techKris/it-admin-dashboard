import { useEffect, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";
import { Link } from "react-router-dom";

type TopologyGraph = {
  nodes: Array<{
    id: string;
    vendor?: string;
    model?: string;
    sysname?: string;
  }>;
  links: Array<{
    source: string;
    target: string;
    local_port: string;
    remote_port: string;
    type: string; // lldp/cdp
  }>;
  stp: Record<string, any>;
  loops: string[];
  vlans: Record<string, any>;
};

export default function TopologyAnalysis() {
  const [topology, setTopology] = useState<TopologyGraph>({
    nodes: [],
    links: [],
    stp: {},
    loops: [],
    vlans: {},
  });

  const [rogues, setRogues] = useState<any[]>([]);
  const [stpIssues, setStpIssues] = useState<any[]>([]);
  const [lacpIssues, setLacpIssues] = useState<any[]>([]);
  const [discovery, setDiscovery] = useState<any>({ switches: [], uplinks: {} });

  const [whatIfSource, setWhatIfSource] = useState("");
  const [whatIfTarget, setWhatIfTarget] = useState("");
  const [whatIfResult, setWhatIfResult] = useState<any>(null);

  const [loading, setLoading] = useState(false);

  // ------------------------------------------------------------
  // LOAD FULL TOPOLOGY ANALYSIS
  // ------------------------------------------------------------

  async function loadTopology() {
    setLoading(true);
    try {
      const resp = await api.post(endpoints.topology.analyze, {
        switches: ["192.168.125.10", "192.168.125.11"], // Replace with dynamic discovery
      });
      setTopology(resp.data);
    } catch (err) {
      console.error(err);
      alert("Failed to load topology");
    } finally {
      setLoading(false);
    }
  }

  // ------------------------------------------------------------
  // ROGUE SWITCH DETECTION
  // ------------------------------------------------------------

  async function checkRogues() {
    try {
      const resp = await api.post(endpoints.topology.rogueCheck, topology);
      setRogues(resp.data.rogue);
    } catch (err) {
      console.error(err);
      alert("Failed to check rogue switches");
    }
  }

  // ------------------------------------------------------------
  // STP ALERTS
  // ------------------------------------------------------------

  async function checkStp() {
    try {
      const resp = await api.post(endpoints.topology.stpCheck, topology);
      setStpIssues(resp.data.issues);
    } catch (err) {
      console.error(err);
      alert("Failed to check STP issues");
    }
  }

  // ------------------------------------------------------------
  // LACP ALERTS
  // ------------------------------------------------------------

  async function checkLacp() {
    try {
      const resp = await api.post(endpoints.topology.lacpCheck, topology);
      setLacpIssues(resp.data.issues);
    } catch (err) {
      console.error(err);
      alert("Failed to check LACP issues");
    }
  }

  // ------------------------------------------------------------
  // AUTOMATED DISCOVERY
  // ------------------------------------------------------------

  async function runDiscovery() {
    try {
      const resp = await api.post(endpoints.topology.discover, {
        seeds: ["192.168.125.10"],
      });
      setDiscovery(resp.data);
    } catch (err) {
      console.error(err);
      alert("Discovery failed");
    }
  }

  // ------------------------------------------------------------
  // WHAT-IF SIMULATION
  // ------------------------------------------------------------

  async function simulate() {
    if (!whatIfSource || !whatIfTarget) {
      alert("Select a source and target link.");
      return;
    }

    try {
      const resp = await api.post(endpoints.topology.simulate, {
        topology,
        source: whatIfSource,
        target: whatIfTarget,
      });
      setWhatIfResult(resp.data);
    } catch (err) {
      console.error(err);
      alert("Simulation failed");
    }
  }

  // Load topology automatically once
  useEffect(() => {
    loadTopology();
  }, []);

  return (
    <div className="grid gap-6 p-4">
      <h2 className="text-lg font-semibold">Topology Analysis</h2>

      <button
        onClick={loadTopology}
        disabled={loading}
        className="px-4 py-2 border rounded bg-blue-100 text-blue-700"
      >
        {loading ? "Loading…" : "Reload Topology"}
      </button>

      {/* ------------------------------------------------------------
          ROGUE SWITCHES
      ------------------------------------------------------------ */}
      <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
        <h3 className="font-semibold mb-2">Rogue Switch Detection</h3>
        <button
          onClick={checkRogues}
          className="px-2 py-1 border rounded bg-red-100 text-red-700"
        >
          Run Rogue Detection
        </button>

        {rogues.length === 0 ? (
          <div className="text-slate-500 text-sm mt-3">No rogue devices detected.</div>
        ) : (
          <ul className="list-disc pl-6 mt-3 space-y-1">
            {rogues.map((r, i) => (
              <li key={i}>
                <span className="font-mono">{r.device}</span> — {r.reason}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* ------------------------------------------------------------
          STP & LACP ALERTS
      ------------------------------------------------------------ */}
      <div className="grid md:grid-cols-2 gap-4">
        
        {/* STP */}
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
          <h3 className="font-semibold mb-2">STP Alerts</h3>
          <button
            onClick={checkStp}
            className="px-2 py-1 border rounded bg-yellow-100 text-yellow-700"
          >
            Run STP Check
          </button>

          {stpIssues.length === 0 ? (
            <div className="text-slate-500 text-sm mt-3">No STP issues.</div>
          ) : (
            <ul className="list-disc pl-6 mt-3 space-y-1">
              {stpIssues.map((i, idx) => (
                <li key={idx}>
                  <strong>{i.device}</strong> — {i.issue}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* LACP */}
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
          <h3 className="font-semibold mb-2">LACP Alerts</h3>
          <button
            onClick={checkLacp}
            className="px-2 py-1 border rounded bg-purple-100 text-purple-700"
          >
            Run LACP Check
          </button>

          {lacpIssues.length === 0 ? (
            <div className="text-slate-500 text-sm mt-3">No LACP issues.</div>
          ) : (
            <ul className="list-disc pl-6 mt-3 space-y-1">
              {lacpIssues.map((i, idx) => (
                <li key={idx}>
                  <strong>{i.devices}</strong> — {i.issue}
                </li>
              ))}
            </ul>
          )}
        </div>

      </div>

      {/* ------------------------------------------------------------
          AUTOMATED DISCOVERY RESULTS
      ------------------------------------------------------------ */}
      <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
        <h3 className="font-semibold mb-2">Automated Switch Discovery</h3>
        <button
          onClick={runDiscovery}
          className="px-2 py-1 border rounded bg-green-100 text-green-700"
        >
          Run Discovery
        </button>

        {discovery.switches.length === 0 ? (
          <div className="text-slate-500 text-sm mt-3">No switches found yet.</div>
        ) : (
          <div className="mt-3">
            <h4 className="font-semibold mb-1">Discovered Switches:</h4>
            <ul className="list-disc pl-6 space-y-1">
              {discovery.switches.map((ip: string) => (
                <li key={ip}>
                  <Link
                    to={`/devices/${ip}`}
                    className="text-blue-600 hover:underline"
                  >
                    {ip}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------
          WHAT-IF SIMULATION
      ------------------------------------------------------------ */}
      <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
        <h3 className="font-semibold mb-3">What‑If Link Failure Simulation</h3>

        <div className="grid md:grid-cols-3 gap-2">
          <div>
            <label className="text-xs text-slate-500">Source Device</label>
            <select
              value={whatIfSource}
              onChange={(e) => setWhatIfSource(e.target.value)}
              className="w-full border rounded px-2 py-1"
            >
              <option value="">—</option>
              {topology.nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.id} ({n.vendor})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-500">Target Device</label>
            <select
              value={whatIfTarget}
              onChange={(e) => setWhatIfTarget(e.target.value)}
              className="w-full border rounded px-2 py-1"
            >
              <option value="">—</option>
              {topology.nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.id} ({n.vendor})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={simulate}
              className="px-3 py-2 border rounded bg-blue-100 text-blue-700"
            >
              Simulate Link Loss
            </button>
          </div>
        </div>

        {whatIfResult && (
          <div className="mt-4">
            <h4 className="font-semibold">Simulation Result</h4>

            <div className="text-sm mt-2">
              <strong>New STP Root:</strong> {whatIfResult.stp_root}
            </div>

            <div className="mt-3">
              <h5 className="font-semibold">Network Components:</h5>
              {whatIfResult.components.map((c: any, idx: number) => (
                <div key={idx} className="text-sm mt-1">
                  Component {idx + 1}: {c.join(", ")}
                </div>
              ))}
            </div>

          </div>
        )}
      </div>
    </div>
  );
}