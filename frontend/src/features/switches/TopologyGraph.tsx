import { useEffect, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";
import { useNavigate } from "react-router-dom";

cytoscape.use(fcose);

export default function TopologyGraph() {
  const [elements, setElements] = useState<any[]>([]);
  const [graphRaw, setGraphRaw] = useState<any>(null);
  const [vlanFilter, setVlanFilter] = useState<number | null>(null);
  const [flashDelta, setFlashDelta] = useState<any>(null);

  const navigate = useNavigate();

  async function loadTopology() {
    try {
      const res = await api.post(endpoints.topology.analyze, {
        switches: ["192.168.125.10", "192.168.125.11"],
      });

      const g = res.data;
      setGraphRaw(g);

      const nodes = g.nodes.map((n: any) => ({
        data: {
          id: n.id,
          label: `${n.id}\n${n.vendor || ""} ${n.model || ""}`,
          vendor: n.vendor,
        },
      }));

      const edges = g.links.map((l: any) => ({
        data: {
          id: `${l.source}-${l.target}`,
          source: l.source,
          target: l.target,
          local: l.local_port,
          remote: l.remote_port,
          type: l.type,
          isLoop: g.loops.includes([l.source, l.target].sort().join("-")),
        },
      }));

      setElements([...nodes, ...edges]);
    } catch (err) {
      console.error(err);
      alert("Failed to load topology");
    }
  }

  useEffect(() => {
    loadTopology();
  }, []);

  useEffect(() => {
    const apiBase =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

    const wsUrl = apiBase.replace("http", "ws") + "/topology/live";
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);

      if (msg.type === "topology_update") {
        const g = msg.full;
        setGraphRaw(g);

        const nodes = g.nodes.map((n: any) => ({
          data: {
            id: n.id,
            label: `${n.id}\n${n.vendor || ""} ${n.model || ""}`,
            vendor: n.vendor,
          },
        }));

        const edges = g.links.map((l: any) => ({
          data: {
            id: `${l.source}-${l.target}`,
            source: l.source,
            target: l.target,
            local: l.local_port,
            remote: l.remote_port,
            type: l.type,
            isLoop: g.loops.includes([l.source, l.target].sort().join("-")),
          },
        }));

        setElements([...nodes, ...edges]);
        setFlashDelta(msg.delta);
        setTimeout(() => setFlashDelta(null), 2000);
      }
    };

    return () => ws.close();
  }, []);

  const vendorColor = (vendor?: string) => {
    if (!vendor) return "#6B7280";
    const v = vendor.toLowerCase();
    if (v.includes("cisco")) return "#3B82F6";
    if (v.includes("aruba") || v.includes("hp") || v.includes("hewlett"))
      return "#10B981";
    if (v.includes("dell")) return "#6366F1";
    if (v.includes("ubiquiti")) return "#F59E0B";
    return "#6B7280";
  };

  const vlanList = graphRaw
    ? Array.from(
        new Set(
          Object.values(graphRaw.vlans || {})
            .flatMap((v: any) => Object.keys(v))
            .map(Number)
        )
      ).sort((a, b) => a - b)
    : [];

  const stylesheet = [
    {
      selector: "node",
      style: {
        "background-color": (ele: any) => vendorColor(ele.data("vendor")),
        label: "data(label)",
        "text-wrap": "wrap",
        "text-max-width": "120px",
        "font-size": "10px",
        color: "#000",
      },
    },
    {
      selector: "edge",
      style: {
        width: (ele: any) => {
          const d = ele.data();
          if (d.isLoop) return 4;
          if (flashDelta) {
            const added = flashDelta.links_added || [];
            const id = `${d.source}|${d.target}`;
            if (added.some(([s, t]: any) => `${s}|${t}` === id)) return 5;
          }
          return 2;
        },
        "line-color": (ele: any) => {
          const d = ele.data();

          if (d.isLoop) return "red";

          if (vlanFilter && graphRaw) {
            const srcV = graphRaw.vlans[d.source]?.[vlanFilter];
            const tgtV = graphRaw.vlans[d.target]?.[vlanFilter];
            if (srcV || tgtV) return "#00C851";
            return "#A0A0A0";
          }

          return "#888";
        },
        label: (ele: any) =>
          `${ele.data("type").toUpperCase()} ${ele.data("local")}→${ele.data(
            "remote"
          )}`,
        "font-size": "8px",
        color: "#333",
        "curve-style": "bezier",
      },
    },
  ];

  return (
    <div className="grid gap-4 p-4">
      <h2 className="text-lg font-semibold">Network Topology</h2>

      <div className="flex gap-4 items-center">
        <button
          onClick={loadTopology}
          className="px-4 py-2 border rounded bg-blue-100 text-blue-700"
        >
          Reload
        </button>

        <select
          className="border rounded px-2 py-1"
          value={vlanFilter || ""}
          onChange={(e) =>
            setVlanFilter(e.target.value ? Number(e.target.value) : null)
          }
        >
          <option value="">All VLANs</option>
          {vlanList.map((v) => (
            <option key={v} value={v}>
              VLAN {v}
            </option>
          ))}
        </select>
      </div>

      <CytoscapeComponent
        elements={elements}
        style={{ width: "100%", height: "650px" }}
        layout={{
          name: "fcose",
          animate: true,
          randomize: false,
          idealEdgeLength: 120,
          nodeSeparation: 200,
        }}
        stylesheet={stylesheet}
        cy={(cy) => {
          cy.on("tap", "node", (evt) => {
            navigate(`/devices/${evt.target.id()}`);
          });
        }}
      />
    </div>
  );
}