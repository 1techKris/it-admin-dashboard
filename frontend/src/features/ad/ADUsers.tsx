// frontend/src/features/ad/ADUsers.tsx

import React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";
import ADUserModal from "./ADUserModal";
import ADDebugPanel from "./ADDebugPanel";
import OUTree from "./OUTree";

/* -----------------------------
   Types
------------------------------ */

type ADUser = {
  dn: string;
  name?: string;
  sam?: string;
  upn?: string;
  enabled: boolean;
  locked: boolean;
  ou?: string;
  lastLogon?: string | null;
  mail?: string | null;
};

type OUTreeNode = {
  type: "ou";
  name: string;
  dn: string;
  users: { name: string; sam: string; dn: string }[];
  children: OUTreeNode[];
};

/* -----------------------------
   Helpers
------------------------------ */

function toBoolParam(val: "" | "true" | "false"): string {
  return val ?? "";
}

function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return String(iso);
  }
}

/* -----------------------------
   Main Component
------------------------------ */

export default function ADUsers() {
  const qc = useQueryClient();

  // Filters/search
  const [q, setQ] = React.useState("");
  const [enabled, setEnabled] = React.useState<"" | "true" | "false">("");
  const [locked, setLocked] = React.useState<"" | "true" | "false">("");
  const [page, setPage] = React.useState(1);

  // Selection
  const [selectedOuDn, setSelectedOuDn] = React.useState<string | null>(null);
  const [selectedUser, setSelectedUser] = React.useState<ADUser | null>(null);

  // OU tree expansion state
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());

  const toggleOu = React.useCallback((dn: string, open?: boolean) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (open === true) next.add(dn);
      else if (open === false) next.delete(dn);
      else {
        if (next.has(dn)) next.delete(dn);
        else next.add(dn);
      }
      return next;
    });
  }, []);

  const clearOu = () => setSelectedOuDn(null);

  const expandAll = (root: OUTreeNode | null) => {
    if (!root) return;
    const stack: OUTreeNode[] = [root];
    const all = new Set<string>();
    while (stack.length) {
      const n = stack.pop()!;
      all.add(n.dn);
      (n.children || []).forEach((c) => stack.push(c));
    }
    setExpanded(all);
  };

  const collapseAll = () => setExpanded(new Set());

  /* ---- Fetch OU tree ---- */
  const {
    data: treeData,
    isLoading: loadingTree,
    isError: errorTree,
  } = useQuery({
    queryKey: ["ad-ou-tree"],
    queryFn: async () => (await api.get<OUTreeNode>(endpoints.ad.ouTree)).data,
  });

  /* ---- Fetch AD users (fetch larger page, filter client-side by OU DN) ---- */
  const {
    data: usersData,
    isLoading: loadingUsers,
    isError: errorUsers,
    refetch,
  } = useQuery({
    queryKey: ["ad-users", { q, enabled, locked, page }],
    queryFn: async () =>
      (await api.get<{ items: ADUser[]; page: number; page_size: number }>(
        endpoints.ad.users(q, toBoolParam(enabled), toBoolParam(locked), page, 1000)
      )).data,
    keepPreviousData: true,
  });

  const users: ADUser[] = usersData?.items || [];

  // Client-side OU filtering (right pane)
  const filteredUsers = React.useMemo(() => {
    if (!selectedOuDn) return users;
    const sel = selectedOuDn.toLowerCase();
    return users.filter((u) => u.dn?.toLowerCase().endsWith(sel));
  }, [users, selectedOuDn]);

  // Drag & drop move user
  const handleDropUser = async (userDn: string, targetOuDn: string) => {
    try {
      await api.post(endpoints.ad.move(userDn), {
        target_ou_dn: targetOuDn,
      });
      qc.invalidateQueries({ queryKey: ["ad-ou-tree"] });
      qc.invalidateQueries({ queryKey: ["ad-users"] });
    } catch (e) {
      console.error(e);
      alert("Failed to move user.");
    }
  };

  /* -----------------------------
     UI
  ------------------------------ */

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Active Directory — Users (OU View)</h2>
      </div>

      {/* AD Debug Panel */}
      <ADDebugPanel />

      {/* Controls */}
      <div className="grid md:grid-cols-3 gap-2 border rounded-xl p-3 bg-white dark:bg-slate-800">
        <div className="md:col-span-1">
          <label className="text-xs text-slate-500">Search</label>
          <input
            className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            placeholder="name, sAM, UPN, mail..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>

        <div>
          <label className="text-xs text-slate-500">Enabled</label>
          <select
            className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            value={enabled}
            onChange={(e) => setEnabled(e.target.value as any)}
          >
            <option value="">All</option>
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-slate-500">Locked</label>
          <select
            className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            value={locked}
            onChange={(e) => setLocked(e.target.value as any)}
          >
            <option value="">All</option>
            <option value="true">Locked</option>
            <option value="false">Not locked</option>
          </select>
        </div>

        <div className="md:col-span-3 flex items-center gap-2">
          <button
            onClick={() => {
              setPage(1);
              refetch();
            }}
            className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Search
          </button>

          {selectedOuDn && (
            <button
              onClick={() => setSelectedOuDn(null)}
              className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
              title={selectedOuDn}
            >
              Clear OU filter
            </button>
          )}
        </div>
      </div>

      {/* Two-pane layout: OU tree | users table */}
      <div className="grid md:grid-cols-3 gap-4">
        {/* OU Tree */}
        <div className="md:col-span-1 border rounded-xl p-3 bg-white dark:bg-slate-800">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold">Directory Tree</div>
            <div className="flex gap-2">
              <button
                className="text-xs px-2 py-1 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
                onClick={() => expandAll(treeData || null)}
              >
                Expand all
              </button>
              <button
                className="text-xs px-2 py-1 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
                onClick={collapseAll}
              >
                Collapse all
              </button>
            </div>
          </div>

          {loadingTree ? (
            <div className="text-sm text-slate-500">Loading OU tree…</div>
          ) : errorTree ? (
            <div className="text-sm text-red-600">
              Failed to load OU tree. Check Network → /ad/ou-tree.
            </div>
          ) : (
            <OUTree
              data={treeData || null}
              expanded={expanded}
              toggle={toggleOu}
              onSelectOu={setSelectedOuDn}
              selectedOuDn={selectedOuDn}
              onDropUser={handleDropUser}
            />
          )}
        </div>

        {/* Users Table */}
        <div className="md:col-span-2">
          <div className="overflow-x-auto border rounded-xl bg-white dark:bg-slate-800">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-700">
                <tr>
                  <th className="p-2 text-left">Name</th>
                  <th className="p-2 text-left">sAM</th>
                  <th className="p-2 text-left">UPN</th>
                  <th className="p-2 text-left">Enabled</th>
                  <th className="p-2 text-left">OU</th>
                  <th className="p-2 text-left">Last Logon</th>
                </tr>
              </thead>
              <tbody>
                {loadingUsers ? (
                  <tr>
                    <td className="p-3 text-sm text-slate-500" colSpan={6}>
                      Loading users…
                    </td>
                  </tr>
                ) : errorUsers ? (
                  <tr>
                    <td className="p-3 text-sm text-red-600" colSpan={6}>
                      Failed to load users.
                    </td>
                  </tr>
                ) : filteredUsers.length ? (
                  filteredUsers.map((u) => (
                    <tr
                      key={u.dn}
                      className="border-t hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer"
                      onClick={() => setSelectedUser(u)}
                      title={u.dn}
                    >
                      <td className="p-2">{u.name || "—"}</td>
                      <td className="p-2">{u.sam || "—"}</td>
                      <td className="p-2">{u.upn || "—"}</td>
                      <td className="p-2">
                        <span
                          className={`px-2 py-1 text-xs rounded border ${
                            u.enabled
                              ? "bg-green-50 border-green-300 text-green-700"
                              : "bg-slate-50 border-slate-300 text-slate-700"
                          }`}
                        >
                          {u.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </td>
                      <td className="p-2">{u.ou || "—"}</td>
                      <td className="p-2">{formatDate(u.lastLogon)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="p-3 text-sm text-slate-500" colSpan={6}>
                      No users match the current filters{selectedOuDn ? " in the selected OU" : ""}.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* User Modal */}
      <ADUserModal
        user={selectedUser}
        onClose={() => setSelectedUser(null)}
        onChanged={() => qc.invalidateQueries({ queryKey: ["ad-users"] })}
      />
    </div>
  );
}