// frontend/src/features/printers/PrinterEditModal.tsx

import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../../lib/api/client";
import { X } from "lucide-react";

export default function PrinterEditModal({ printer, onClose }: any) {
  const queryClient = useQueryClient();
  const [friendlyName, setFriendlyName] = useState(printer.friendlyName ?? "");

  const saveMutation = useMutation({
    mutationFn: () =>
      api.put(`/printers/${printer.id}`, { friendlyName }),
    onSuccess: () => {
      queryClient.invalidateQueries(["printers"]);
      queryClient.invalidateQueries(["printers-detailed"]);
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-[var(--bg-card)] rounded-lg p-6 w-full max-w-md shadow-xl">

        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold dark:text-white">Edit Printer</h2>
          <button onClick={onClose}>
            <X size={20} className="text-slate-700 dark:text-slate-300" />
          </button>
        </div>

        {/* Form */}
        <div>
          <label className="text-sm dark:text-[var(--text-muted)]">Friendly Name</label>
          <input
            value={friendlyName}
            onChange={(e) => setFriendlyName(e.target.value)}
            className="mt-1 w-full border p-2 rounded dark:bg-[var(--bg-input)] dark:border-[var(--border-color)] dark:text-white"
            placeholder="e.g. Upstairs Colour Printer"
          />
        </div>

        {/* Buttons */}
        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-3 py-1 border rounded dark:border-[var(--border-color)]"
          >
            Cancel
          </button>

          <button
            onClick={() => saveMutation.mutate()}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Save
          </button>
        </div>

      </div>
    </div>
  );
}