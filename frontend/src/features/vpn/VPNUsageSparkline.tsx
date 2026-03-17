// frontend/src/features/vpn/VPNUsageSparkline.tsx

import { LineChart, Line, ResponsiveContainer } from "recharts";
import useVPNHistory from "../../lib/hooks/useVPNHistory";

export default function VPNUsageSparkline() {
  const { data } = useVPNHistory();
  if (!data || data.length === 0) return null;

  const recent = data.slice(-40); // last 40 data points

  return (
    <div className="h-12 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={recent}>
          <Line
            type="monotone"
            dataKey="count"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}