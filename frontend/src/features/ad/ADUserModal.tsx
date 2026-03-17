import { useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";

export default function ADUserModal({
  user,
  onClose,
  onChanged,
}: {
  user: any;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [pwd, setPwd] = useState("");
  const [mustChange, setMustChange] = useState(true);
  const [moveOu, setMoveOu] = useState("");

  if (!user) return null;

  async function call(promise: Promise<any>, okMsg = "Done") {
    try {
      await promise;
      alert(okMsg);
      onChanged();
    } catch (e: any) {
      console.error(e);
      alert("Action failed.");
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-2xl p-6 relative">
        <button onClick={onClose} className="absolute top-2 right-2 text-slate-500 hover:text-slate-700">✕</button>
        <h3 className="text-lg font-semibold mb-2">{user.name || user.sam}</h3>
        <div className="text-xs text-slate-500 mb-4 break-all">{user.dn}</div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="border rounded-xl p-3">
            <div className="text-sm font-medium mb-2">Reset Password</div>
            <input
              className="w-full border rounded px-3 py-2 mb-2 dark:bg-slate-700 dark:border-slate-600"
              type="password"
              placeholder="New password"
              value={pwd}
              onChange={(e) => setPwd(e.target.value)}
            />
            <label className="text-xs flex items-center gap-2 mb-2">
              <input type="checkbox" checked={mustChange} onChange={(e) => setMustChange(e.target.checked)} />
              Must change at next logon
            </label>
            <button
              className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
              onClick={() => call(api.post(endpoints.ad.reset(user.dn), { new_password: pwd, must_change: mustChange }), "Password reset")}
              disabled={!pwd}
            >
              Reset Password
            </button>
          </div>

          <div className="border rounded-xl p-3">
            <div className="text-sm font-medium mb-2">Account Control</div>
            {user.enabled ? (
              <button
                className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700 w-full mb-2"
                onClick={() => call(api.post(endpoints.ad.disable(user.dn)), "User disabled")}
              >
                Disable
              </button>
            ) : (
              <button
                className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700 w-full mb-2"
                onClick={() => call(api.post(endpoints.ad.enable(user.dn)), "User enabled")}
              >
                Enable
              </button>
            )}
            <button
              className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700 w-full"
              onClick={() => call(api.post(endpoints.ad.unlock(user.dn)), "User unlocked")}
            >
              Unlock
            </button>
          </div>

          <div className="border rounded-xl p-3 md:col-span-2">
            <div className="text-sm font-medium mb-2">Move User to OU</div>
            <input
              className="w-full border rounded px-3 py-2 mb-2 dark:bg-slate-700 dark:border-slate-600"
              placeholder='Target OU DN, e.g. OU=Sales,OU=Users,DC=yourdomain,DC=local'
              value={moveOu}
              onChange={(e) => setMoveOu(e.target.value)}
            />
            <button
              className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
              onClick={() => call(api.post(endpoints.ad.move(user.dn), { target_ou_dn: moveOu }), "User moved")}
              disabled={!moveOu}
            >
              Move
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}