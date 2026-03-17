// frontend/src/features/switches/Switches.tsx

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";
import SwitchDetailModal from "./SwitchDetailModal";

export default function Switches() {
  const [selectedSwitch, setSelectedSwitch] = useState(null);

  const switches = useQuery({
    queryKey: ["switches"],
    queryFn: () => api.get("/switches").then((res) => res.data),
    refetchInterval: 10000,
  });

  const list = switches.data ?? [];

  return (
    <div className="space-y-6">

      <h1 className="text-2xl font-semibold dark:text-white">
        Network Switches
      </h1>

      <div className="grid grid-cols-3 gap-4">
        {list.map((sw: any) => (
          <div
            key={sw.id}
            className="card p-4 rounded-lg cursor-pointer hover:shadow-md transition"
            onClick={() => setSelectedSwitch(sw)}
          >
            <div className="text-lg font-medium dark:text-white">
              {sw.name}
            </div>

            <div className="text-xs text-slate-500 dark:text-[var(--text-muted)] mb-2">
              {sw.ip} — {sw.vendor} {sw.model}
            </div>

            <div className="flex items-center gap-2 text-sm">
              <span
                className={`w-2 h-2 rounded-full ${
                  sw.status === "online" ? "bg-green-500" : "bg-red-500"
                }`}
              ></span>
              {sw.status}
            </div>

            <div className="text-xs mt-2 text-slate-500 dark:text-[var(--text-muted)]">
              Ports: {sw.ports_up}/{sw.ports_total}
            </div>
          </div>
        ))}

        {list.length === 0 && (
          <div className="text-slate-500 dark:text-[var(--text-muted)]">
            No switches found.
          </div>
        )}
      </div>

      {/* DETAIL MODAL */}
      {selectedSwitch && (
        <SwitchDetailModal
          sw={selectedSwitch}
          onClose={() => setSelectedSwitch(null)}
        />
      )}
    </div>
  );
}