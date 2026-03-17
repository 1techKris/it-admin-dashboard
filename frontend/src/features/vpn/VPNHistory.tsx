// frontend/src/features/vpn/VPNHistory.tsx

import React from "react";
import useVPNHistory from "../../lib/hooks/useVPNHistory";
import VPNUsageChart from "./VPNUsageChart";

export default function VPNHistory() {
  const { data, isLoading } = useVPNHistory();

  if (isLoading) return <div className="p-4">Loading...</div>;

  return (
    <div className="p-4 grid gap-4">
      <VPNUsageChart />

      <div className="border rounded-xl bg-white dark:bg-slate-800 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-700">
            <tr>
              <th className="p-2 text-left">Timestamp</th>
              <th className="p-2 text-left">Username</th>
              <th className="p-2 text-left">IPv4</th>
              <th className="p-2 text-left">Connected From</th>
              <th className="p-2 text-left">Country</th>
              <th className="p-2 text-left">City</th>
              <th className="p-2 text-left">ISP</th>
            </tr>
          </thead>

          <tbody>
            {data?.map((p: any, i: number) => (
              <tr key={i} className="border-t">
                <td className="p-2">
                  {new Date(p.ts).toLocaleString()}
                </td>
                <td className="p-2">{p.username}</td>
                <td className="p-2">{p.ipv4}</td>
                <td className="p-2">{p.connected_from}</td>
                <td className="p-2">{p.geo_country}</td>
                <td className="p-2">{p.geo_city}</td>
                <td className="p-2">{p.geo_isp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}