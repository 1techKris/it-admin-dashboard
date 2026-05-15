import { useEffect, useState } from "react";
import api from "../../lib/api/client";
import { RefreshCw, XCircle } from "lucide-react";

type BCSess = {
  sessionId: number;
  user: string;
  clientType: string;
  loginTime: string | null;
  lastActive: string | null;
  idleTime: string;
};

export default function BCSessions() {
  const [sessions, setSessions] = useState<BCSess[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadSessions() {
    try {
      setLoading(true);
      setError(null);

      const { data } = await api.get("/bc/sessions");
      setSessions(Array.isArray(data) ? data : []);
    } catch {
      setError("Failed to load Business Central sessions.");
    } finally {
      setLoading(false);
    }
  }

  async function killSession(id: number) {
    const ok = confirm(
      `Terminate Business Central session ${id}?\n\nThe user will be disconnected immediately.`
    );
    if (!ok) return;

    try {
      await api.post(`/bc/sessions/${id}/kill`);
      await loadSessions();
    } catch {
      alert("Failed to terminate session.");
    }
  }

  useEffect(() => {
    loadSessions();
  }, []);

  return (
    <div className="p-4 grid gap-4">

      {/* Header */}
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold">
          Business Central Sessions
        </h2>

        <button
          onClick={loadSessions}
          disabled={loading}
          className="flex items-center gap-1 text-sm px-3 py-1 border rounded
                     hover:bg-slate-50 dark:hover:bg-slate-700"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="text-rose-600 text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="border rounded-lg overflow-hidden dark:border-slate-600">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 dark:bg-slate-700">
            <tr>
              <th className="p-2 text-left">User</th>
              <th className="text-left">Client</th>
              <th className="text-left">Login Time</th>
              <th className="text-left">Last Active</th>
              <th className="text-left">Idle</th>
              <th className="w-20"></th>
            </tr>
          </thead>

          <tbody>
            {sessions.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="p-4 text-center text-slate-500">
                  No active Business Central sessions.
                </td>
              </tr>
            )}

            {sessions.map((s) => (
              <tr
                key={s.sessionId}
                className="border-t dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <td className="p-2 font-mono">{s.user}</td>
                <td>{s.clientType}</td>

                <td>
                  {s.loginTime
                    ? new Date(s.loginTime).toLocaleString()
                    : "—"}
                </td>

                <td>
                  {s.lastActive
                    ? new Date(s.lastActive).toLocaleString()
                    : "—"}
                </td>

                <td>{s.idleTime}</td>

                <td className="p-1 text-right">
                  <button
                    onClick={() => killSession(s.sessionId)}
                    className="text-rose-600 hover:text-rose-800"
                    title="Terminate session"
                  >
                    <XCircle size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}