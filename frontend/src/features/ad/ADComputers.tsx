import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";

export default function ADComputers() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ad-computers", { q, page }],
    queryFn: async () => (await api.get(endpoints.ad.computers(q, page, 50))).data,
    keepPreviousData: true,
  });

  const rows = useMemo(() => data?.items || [], [data]);

  return (
    <div className="grid gap-3">
      <h2 className="text-lg font-semibold">Active Directory — Computers</h2>

      <div className="grid md:grid-cols-3 gap-2 border rounded-xl p-3 bg-white dark:bg-slate-800">
        <div className="md:col-span-2">
          <label className="text-xs text-slate-500">Search computers</label>
          <input
            className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            placeholder="name, cn..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="self-end">
          <button
            className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
            onClick={() => { setPage(1); refetch(); }}
          >
            Search
          </button>
        </div>
      </div>

      <div className="overflow-x-auto border rounded-xl bg-white dark:bg-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-700">
            <tr>
              <th className="p-2 text-left">Name</th>
              <th className="p-2 text-left">OS</th>
              <th className="p-2 text-left">Version</th>
              <th className="p-2 text-left">OU</th>
              <th className="p-2 text-left">Enabled</th>
              <th className="p-2 text-left">Last Logon</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c: any) => (
              <tr key={c.dn} className="border-t">
                <td className="p-2">{c.name}</td>
                <td className="p-2">{c.os || "—"}</td>
                <td className="p-2">{c.osVersion || "—"}</td>
                <td className="p-2">{c.ou || "—"}</td>
                <td className="p-2">
                  <span className={`px-2 py-1 text-xs rounded border ${c.enabled ? "bg-green-50 border-green-300 text-green-700" : "bg-slate-50 border-slate-300 text-slate-700"}`}>
                    {c.enabled ? "Enabled" : "Disabled"}
                  </span>
                </td>
                <td className="p-2">{c.lastLogon ? new Date(c.lastLogon).toLocaleString() : "—"}</td>
              </tr>
            ))}
            {!rows.length && !isLoading && (
              <tr>
                <td className="p-3 text-sm text-slate-500" colSpan={6}>No computers found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}