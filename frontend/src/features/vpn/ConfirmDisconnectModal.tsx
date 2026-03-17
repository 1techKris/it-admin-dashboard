// frontend/src/features/vpn/ConfirmDisconnectModal.tsx

import React from "react";

export default function ConfirmDisconnectModal({
  open,
  onClose,
  onConfirm,
  session,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  session: any | null;
}) {
  if (!open || !session) return null;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full shadow-xl">
        <h2 className="text-lg font-semibold mb-3">Disconnect VPN User</h2>

        <div className="text-sm grid gap-1 mb-3">
          <div><b>User:</b> {session.Username}</div>
          <div><b>IPv4:</b> {session.ClientIPv4Address || "—"}</div>
          <div><b>Connected From:</b> {session.ConnectedFrom || "—"}</div>
          <div><b>Connected Since:</b> {session.ConnectionStartTime || "—"}</div>
        </div>

        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-slate-200 dark:bg-slate-700"
          >
            Cancel
          </button>

          <button
            onClick={onConfirm}
            className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700"
          >
            Disconnect
          </button>
        </div>
      </div>
    </div>
  );
}