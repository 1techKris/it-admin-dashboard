// frontend/src/features/switches/SwitchDetailModal.tsx

import React from "react";
import { X } from "lucide-react";

export default function SwitchDetailModal({ sw, onClose }: any) {

  return (
    <>
      {/* BACKDROP */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* MODAL */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-[var(--bg-card)] p-6 rounded-lg w-full max-w-3xl shadow-xl">

          {/* HEADER */}
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold dark:text-white">
              {sw.name}
            </h2>
            <button onClick={onClose}>
              <X size={20} className="text-slate-700 dark:text-slate-300" />
            </button>
          </div>

          {/* SWITCH INFO */}
          <div className="grid grid-cols-2 gap-4 mb-6 text-sm dark:text-white">
            <div>
              <strong>IP:</strong> {sw.ip}<br />
              <strong>Model:</strong> {sw.vendor} {sw.model}<br />
              <strong>Serial:</strong> {sw.serial || "Unknown"}<br />
              <strong>Firmware:</strong> {sw.firmware || "Unknown"}
            </div>

            <div>
              <strong>Status:</strong> {sw.status}<br />
              <strong>Uptime:</strong> {sw.uptime}<br />
              <strong>Temperature:</strong> {sw.temperature ?? "N/A"}°C<br />
            </div>
          </div>

          {/* PORT TABLE */}
          <h3 className="text-lg font-medium mb-2 dark:text-white">
            Ports
          </h3>

          <table className="w-full text-sm">
            <thead>
              <tr className="border-b dark:border-[var(--border-color)] text-left">
                <th className="py-2">Port</th>
                <th className="py-2">Status</th>
                <th className="py-2">Speed</th>
                <th className="py-2">PoE</th>
                <th className="py-2">VLAN</th>
                <th className="py-2">LLDP</th>
              </tr>
            </thead>

            <tbody>
              {sw.ports?.map((p: any) => (
                <tr key={p.id} className="border-b dark:border-[var(--border-color)]">
                  <td className="py-2">{p.name}</td>

                  <td className="py-2">
                    <span
                      className={`w-2 h-2 inline-block rounded-full ${
                        p.status === "up" ? "bg-green-500" : "bg-red-500"
                      }`}
                    ></span>{" "}
                    {p.status}
                  </td>

                  <td className="py-2">{p.speed || "—"}</td>
                  <td className="py-2">{p.poe ? `${p.poe} W` : "—"}</td>
                  <td className="py-2">{p.vlan || "—"}</td>

                  <td className="py-2">
                    {p.lldp?.systemName
                      ? `${p.lldp.systemName} (${p.lldp.portId})`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

        </div>
      </div>
    </>
  );
}