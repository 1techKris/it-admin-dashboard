// frontend/src/features/vpn/VPNUsageChart.tsx

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import useVPNHistory from "../../lib/hooks/useVPNHistory";

export default function VPNUsageChart() {
  const { data, isLoading } = useVPNHistory();

  if (isLoading) return <div>Loading chart…</div>;
  if (!data || data.length === 0) return <div>No VPN history yet.</div>;

  return (
    <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
      <h3 className="font-semibold text-lg mb-2">VPN Usage (Last 24h)</h3>

      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="vpnColor" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.6} />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />

          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["auto", "auto"]}
            tickFormatter={(v) => new Date(v).toLocaleTimeString()}
          />

          <YAxis allowDecimals={false} />
          <Tooltip
            labelFormatter={(v) => new Date(v).toLocaleString()}
            formatter={(v) => [`${v} users`, "Active"]}
          />

          <Area
            type="monotone"
            dataKey="count"
            stroke="#3b82f6"
            fill="url(#vpnColor)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}