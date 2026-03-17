import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

export default function LiveCharts() {
  const [data, setData] = useState(
    Array.from({ length: 20 }, (_, i) => ({
      t: i,
      cpu: Math.random() * 70 + 20,
      mem: Math.random() * 50 + 30,
      net: Math.random() * 80 + 10,
    }))
  );

  useEffect(() => {
    const id = setInterval(() => {
      setData((prev) => {
        const t = prev[prev.length - 1].t + 1;
        const next = {
          t,
          cpu: clamp(prev[prev.length - 1].cpu + (Math.random() - 0.5) * 10),
          mem: clamp(prev[prev.length - 1].mem + (Math.random() - 0.5) * 8),
          net: clamp(prev[prev.length - 1].net + (Math.random() - 0.5) * 12),
        };
        return [...prev.slice(1), next];
      });
    }, 1500);

    return () => clearInterval(id);
  }, []);

  function clamp(num: number) {
    return Math.max(5, Math.min(95, num));
  }

  return (
    <div className="rounded-2xl shadow-sm bg-white dark:bg-slate-800 p-4">
      <div className="text-sm font-medium mb-2">Resource Trends</div>

      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="cpu" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="mem" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="net" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="t" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Legend />

            <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#3b82f6" fill="url(#cpu)" />
            <Area type="monotone" dataKey="mem" name="Memory %" stroke="#22c55e" fill="url(#mem)" />
            <Area type="monotone" dataKey="net" name="Network %" stroke="#f59e0b" fill="url(#net)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}