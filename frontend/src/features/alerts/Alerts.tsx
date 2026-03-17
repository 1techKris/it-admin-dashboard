// frontend/src/features/alerts/Alerts.tsx

import React from "react";
import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";
import { Bell, AlertTriangle } from "lucide-react";

export default function Alerts() {

  const alerts = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api.get("/alerts").then(res => res.data),
    refetchInterval: 5000,
  });

  const items = Array.isArray(alerts.data) ? alerts.data : [];

  const severityColor = (sev: string) => {
    switch (sev) {
      case "Critical":
        return "text-red-600 dark:text-red-400";
      case "Warning":
        return "text-yellow-600 dark:text-yellow-400";
      case "Info":
        return "text-blue-600 dark:text-blue-400";
      default:
        return "text-slate-600 dark:text-slate-300";
    }
  };

  return (
    <div className="space-y-6">

      <h1 className="text-2xl font-semibold flex items-center gap-2 dark:text-white">
        <Bell size={22} /> Alerts
      </h1>

      <div className="card rounded-lg p-4">

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-600 dark:text-slate-300 border-b border-slate-300 dark:border-slate-700">
              <th className="py-2">ID</th>
              <th className="py-2">Severity</th>
              <th className="py-2">Source</th>
              <th className="py-2">Message</th>
              <th className="py-2">Time</th>
            </tr>
          </thead>

          <tbody>

            {items.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center dark:text-slate-400">
                  No alerts found.
                </td>
              </tr>
            )}

            {items.map((alert: any) => (
              <tr
                key={alert.id}
                className="border-b border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
              >

                {/* ID */}
                <td className="py-2">{alert.id}</td>

                {/* Severity */}
                <td className={`py-2 font-semibold flex items-center gap-1 ${severityColor(alert.severity)}`}>
                  <AlertTriangle size={14} />
                  {alert.severity}
                </td>

                {/* Source */}
                <td className="py-2">{alert.source}</td>

                {/* Message */}
                <td className="py-2">{alert.message}</td>

                {/* Time */}
                <td className="py-2">{alert.time}</td>

              </tr>
            ))}

          </tbody>
        </table>

      </div>
    </div>
  );
}