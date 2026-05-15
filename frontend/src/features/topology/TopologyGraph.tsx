import { useEffect, useState, useCallback, useRef } from "react";
import api from "../../lib/api/client";
import { ForceGraph2D } from "react-force-graph";
import { useNavigate } from "react-router-dom";
import { endpoints } from "../../lib/api/endpoints";

export default function TopologyGraph() {
  const [graph, setGraph] = useState<any>({ nodes: [], links: [] });
  const nav = useNavigate();
  const graphRef = useRef<any>(null);

  async function load() {
    const res = await api.get(endpoints.switch.topology);
    setGraph(res.data);

    // Center graph
    setTimeout(() => {
      graphRef.current?.zoomToFit(400, 50);
    }, 300);
  }

  useEffect(() => {
    load();
  }, []);

  const nodeColor = useCallback((node: any) => {
    const vendor = (node.vendor || "").toLowerCase();
    if (vendor.includes("cisco")) return "#2b6cb0";
    if (vendor.includes("hp") || vendor.includes("aruba")) return "#9f7aea";
    if (vendor.includes("dell")) return "#ed8936";
    return "#4a5568";
  }, []);

  return (
    <div className="w-full h-[85vh] border rounded-2xl bg-white dark:bg-slate-800 p-2">
      <h2 className="text-lg font-semibold mb-2 px-2">Network Topology</h2>

      <ForceGraph2D
        ref={graphRef}
        graphData={graph}
        nodeLabel={(n: any) => `${n.name} (${n.ip})`}
        nodeAutoColorBy="vendor"
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.name;
          const fontSize = 14 / globalScale;

          ctx.fillStyle = nodeColor(node);
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, 8, 0, 2 * Math.PI, false);
          ctx.fill();

          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.textAlign = "left";
          ctx.textBaseline = "middle";
          ctx.fillStyle = "black";
          ctx.fillText(label, node.x! + 10, node.y!);
        }}
        linkLabel={(link: any) => `Port ${link.local_port || ""}`}
        onNodeClick={(node: any) => {
          nav(`/switches/${node.id}`);
        }}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
      />
    </div>
  );
}