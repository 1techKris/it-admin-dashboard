// frontend/src/features/printers/Printers.tsx

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../../lib/api/client";
import PrinterDetailModal from "./PrinterDetailModal";

export default function Printers() {
  const [selectedPrinter, setSelectedPrinter] = useState(null);
  const [printerToDelete, setPrinterToDelete] = useState(null);
  const queryClient = useQueryClient();

  // Load the basic printer list
  const baseList = useQuery({
    queryKey: ["printers"],
    queryFn: () => api.get("/printers").then((res) => res.data),
  });

  const list = baseList.data ?? [];

  // UTAX / Kyocera CMYK parser (Final Version)
  const getTonerFromSupplies = (supplies: any[]) => {
    if (!supplies || supplies.length === 0) return null;

    const toner = { C: null, M: null, Y: null, K: null };

    for (const s of supplies) {
      const desc = (s.description || "").toUpperCase();
      const pct = s.percent;
      if (pct == null) continue;

      // UTAX = neat trailing letter
      if (desc.endsWith(" C")) { toner.C = pct; continue; }
      if (desc.endsWith(" M")) { toner.M = pct; continue; }
      if (desc.endsWith(" Y")) { toner.Y = pct; continue; }
      if (desc.endsWith(" K")) { toner.K = pct; continue; }

      // fallback generic
      if (desc.includes("CYAN")) { toner.C = pct; continue; }
      if (desc.includes("MAGENTA")) { toner.M = pct; continue; }
      if (desc.includes("YELLOW")) { toner.Y = pct; continue; }
      if (desc.includes("BLACK")) { toner.K = pct; continue; }
    }

    const hasColour = toner.C || toner.M || toner.Y;
    if (!hasColour) return { K: toner.K };

    return toner;
  };

  // Fetch supplies for each printer
  const detailedList = useQuery({
    queryKey: ["printer-details"],
    enabled: list.length > 0,
    queryFn: async () => {
      const result = await Promise.all(
        list.map((p) =>
          api.get(`/printers/${p.id}`).then((res) => ({
            ...p,
            supplies: res.data.supplies,
          }))
        )
      );
      return result;
    },
  });

  const printers = detailedList.data?.map((p) => ({
    ...p,
    toner: getTonerFromSupplies(p.supplies),
  })) ?? [];

  // Delete printer
  const deletePrinter = useMutation({
    mutationFn: (id: number) => api.delete(`/printers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries(["printers"]);
      setPrinterToDelete(null);
    },
  });

  const colours: any = {
    C: "#00b7ff",
    M: "#ff2fb2",
    Y: "#ffd600",
    K: "#666666",
  };

  return (
    <div className="space-y-6">

      <h1 className="text-2xl font-semibold dark:text-white">Printers</h1>

      <div className="grid grid-cols-3 gap-4">

        {printers.map((p) => {
          const keys = p.toner ? Object.keys(p.toner) : [];

          return (
            <div
              key={p.id}
              onClick={() => setSelectedPrinter(p)}
              className="card p-4 rounded-lg relative hover:shadow-md transition cursor-pointer"
            >

              {/* Delete button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setPrinterToDelete(p);
                }}
                className="absolute top-2 right-2 p-1 rounded hover:bg-red-200 dark:hover:bg-red-900"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                     className="w-4 h-4 text-red-600 dark:text-red-400">
                  <path d="M3 6h18M8 6V4h8v2M10 11v6M14 11v6M5 6l1 14h12l1-14"/>
                </svg>
              </button>

              <div className="text-lg font-medium dark:text-white">
                {p.friendlyName || p.name}
              </div>

              <div className="text-xs text-slate-500 dark:text-[var(--text-muted)] mb-3">
                {p.status}
              </div>

              {/* No toner */}
              {!p.toner && (
                <div className="italic text-xs text-slate-500 dark:text-[var(--text-muted)]">
                  No toner data available
                </div>
              )}

              {/* Toner bars */}
              {p.toner && (
                <div className="space-y-2 mt-2">
                  {keys.map((t) => (
                    <div key={t}>
                      <div className="flex justify-between text-xs dark:text-white">
                        <span>{t}</span>
                        <span>{p.toner[t]}%</span>
                      </div>
                      <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded">
                        <div
                          className="h-2 rounded"
                          style={{
                            width: `${p.toner[t]}%`,
                            backgroundColor: colours[t],
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

            </div>
          );
        })}

        {printers.length === 0 && (
          <div className="text-slate-500 dark:text-[var(--text-muted)]">
            No printers found.
          </div>
        )}

      </div>

      {/* Delete confirmation modal */}
      {printerToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-[var(--bg-card)] p-6 rounded-lg shadow-xl w-full max-w-sm">

            <h2 className="text-lg font-semibold dark:text-white mb-4">
              Remove Printer
            </h2>

            <p className="text-sm dark:text-[var(--text-muted)] mb-6">
              Remove{" "}
              <strong>{printerToDelete.friendlyName || printerToDelete.name}</strong>?
            </p>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setPrinterToDelete(null)}
                className="px-3 py-1 border rounded dark:border-[var(--border-color)]"
              >
                Cancel
              </button>

              <button
                onClick={() => deletePrinter.mutate(printerToDelete.id)}
                className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Remove
              </button>
            </div>

          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedPrinter && (
        <PrinterDetailModal
          printer={selectedPrinter}
          onClose={() => setSelectedPrinter(null)}
        />
      )}

    </div>
  );
}