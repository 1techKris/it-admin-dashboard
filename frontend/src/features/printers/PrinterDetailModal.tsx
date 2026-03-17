// frontend/src/features/printers/PrinterDetailModal.tsx

import React, { useState } from "react";
import { X } from "lucide-react";
import PrinterEditModal from "./PrinterEditModal";

export default function PrinterDetailModal({ printer, onClose }: any) {
  const [showEdit, setShowEdit] = useState(false);

  // ---------------------------------------
  // FINAL UTAX + GENERIC TONER PARSER
  // ---------------------------------------
  const getTonerFromSupplies = (supplies: any[]) => {
    if (!supplies || supplies.length === 0) return null;

    const toner = { C: null, M: null, Y: null, K: null };

    for (const s of supplies) {
      const desc = (s.description || "").toUpperCase();
      const pct = s.percent;
      if (pct == null) continue;

      // 🎯 BEST MATCH → UTAX naming always ends with space + C/M/Y/K
      if (desc.endsWith(" C")) { toner.C = pct; continue; }
      if (desc.endsWith(" M")) { toner.M = pct; continue; }
      if (desc.endsWith(" Y")) { toner.Y = pct; continue; }
      if (desc.endsWith(" K")) { toner.K = pct; continue; }

      // Generic backup detection
      if (desc.includes("CYAN")) { toner.C = pct; continue; }
      if (desc.includes("MAGENTA")) { toner.M = pct; continue; }
      if (desc.includes("YELLOW")) { toner.Y = pct; continue; }
      if (desc.includes("BLACK")) { toner.K = pct; continue; }
    }

    // Mono printer fallback → only K detected
    const hasColour = toner.C || toner.M || toner.Y;
    if (!hasColour) return { K: toner.K };

    return toner;
  };

  const toner = getTonerFromSupplies(printer.supplies);
  const keys = toner ? Object.keys(toner) : [];

  const colours: any = {
    C: "#00b7ff",
    M: "#ff2fb2",
    Y: "#ffd600",
    K: "#666666",
  };

  return (
    <>
      {/* BACKDROP */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* MODAL */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-[var(--bg-card)] p-6 w-full max-w-lg rounded-lg shadow-xl">

          {/* HEADER */}
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold dark:text-white">
              {printer.friendlyName || printer.name}
            </h2>
            <button onClick={onClose}>
              <X size={20} className="text-slate-700 dark:text-slate-300" />
            </button>
          </div>

          {/* EDIT BUTTON */}
          <button
            onClick={() => setShowEdit(true)}
            className="border px-3 py-1 rounded mb-4 dark:border-[var(--border-color)] hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            Edit Printer
          </button>

          {/* PRINTER INFO */}
          <div className="space-y-2 text-sm dark:text-white">
            <div><strong>Name:</strong> {printer.name}</div>
            <div><strong>IP:</strong> {printer.ip}</div>
            <div><strong>Status:</strong> {printer.status}</div>
            <div><strong>Model:</strong> {printer.model ?? "Unknown"}</div>
            <div><strong>Serial:</strong> {printer.serial ?? "Unknown"}</div>
            <div>
              <strong>Last Seen:</strong>{" "}
              {printer.last_seen ? new Date(printer.last_seen).toLocaleString() : "Never"}
            </div>
          </div>

          {/* TONER */}
          {!toner && (
            <div className="italic text-slate-500 dark:text-[var(--text-muted)] mt-4">
              No toner data available
            </div>
          )}

          {toner && (
            <div className="mt-4 space-y-3">
              {keys.map((t) => (
                <div key={t}>
                  <div className="flex justify-between text-xs dark:text-white">
                    <span>{t}</span>
                    <span>{toner[t]}%</span>
                  </div>

                  <div className="w-full h-3 bg-slate-200 dark:bg-slate-700 rounded">
                    <div
                      className="h-3 rounded"
                      style={{
                        width: `${toner[t]}%`,
                        backgroundColor: colours[t],
                      }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          )}

        </div>
      </div>

      {/* EDIT MODAL */}
      {showEdit && (
        <PrinterEditModal
          printer={printer}
          onClose={() => setShowEdit(false)}
        />
      )}
    </>
  );
}