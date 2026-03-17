import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";

export default function ADGroups() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["ad-groups", { q, page }],
    queryFn: async () => (await api.get(endpoints.ad.groups(q, page, 50))).data,
    keepPreviousData: true,
  });

  const rows = useMemo(() => data?.items || [], [data]);
  const [selected, setSelected] = useState<any | null>(null);
  const { data: members } = useQuery({
    enabled: !!selected,
    queryKey: ["ad-group-members", selected?.dn],
    queryFn: async () => (await api.get(endpoints.ad.groupMembers(selected!.dn))).data,
  });

  const addMember = useMutation({
    mutationFn: async ({ group_dn, member_dn }: any) =>
      (await api.post(endpoints.ad.groupAddMember(group_dn), { member_dn })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ad-group-members", selected?.dn] }),
  });
  const removeMember = useMutation({
    mutationFn: async ({ group_dn, member_dn }: any) =>
      (await api.post(endpoints.ad.groupRemoveMember(group_dn), { member_dn })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ad-group-members", selected?.dn] }),
  });

  const [newMemberDn, setNewMemberDn] = useState("");

  return (
    <div className="grid gap-3">
      <h2 className="text-lg font-semibold">Active Directory — Groups</h2>

      <div className="grid md:grid-cols-3 gap-2 border rounded-xl p-3 bg-white dark:bg-slate-800">
        <div className="md:col-span-2">
          <label className="text-xs text-slate-500">Search groups</label>
          <input
            className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
            placeholder="cn, name..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="self-end">
          <button className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700" onClick={() => setPage(1)}>
            Search
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        <div className="overflow-x-auto border rounded-xl bg-white dark:bg-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700">
              <tr>
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Description</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((g: any) => (
                <tr
                  key={g.dn}
                  className={`border-t hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer ${selected?.dn === g.dn ? "bg-slate-100 dark:bg-slate-700" : ""}`}
                  onClick={() => setSelected(g)}
                >
                  <td className="p-2">{g.name}</td>
                  <td className="p-2">{g.description || "—"}</td>
                </tr>
              ))}
              {!rows.length && !isLoading && (
                <tr>
                  <td className="p-3 text-sm text-slate-500" colSpan={2}>No groups found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="border rounded-xl p-3 bg-white dark:bg-slate-800">
          {!!selected ? (
            <>
              <div className="text-sm font-semibold mb-2">Members of {selected.name}</div>
              <div className="text-xs text-slate-500 mb-3 break-all">{selected.dn}</div>

              <div className="flex gap-2 mb-2">
                <input
                  className="flex-1 border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
                  placeholder="Enter member DN to add"
                  value={newMemberDn}
                  onChange={(e) => setNewMemberDn(e.target.value)}
                />
                <button
                  className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
                  onClick={async () => {
                    if (!newMemberDn) return;
                    try {
                      await addMember.mutateAsync({ group_dn: selected.dn, member_dn: newMemberDn });
                      setNewMemberDn("");
                    } catch { alert("Failed to add member"); }
                  }}
                >
                  Add
                </button>
              </div>

              <div className="max-h-80 overflow-auto border rounded p-2">
                {(members?.members || []).map((m: any) => (
                  <div key={m.dn} className="flex items-center justify-between border-b py-1 text-sm">
                    <div className="pr-2">
                      <div className="font-medium">{m.name || m.sam || m.dn}</div>
                      <div className="text-xs text-slate-500 break-all">{m.dn}</div>
                    </div>
                    <button
                      className="text-xs px-2 py-1 border rounded hover:bg-slate-50"
                      onClick={async () => {
                        try {
                          await removeMember.mutateAsync({ group_dn: selected.dn, member_dn: m.dn });
                        } catch { alert("Failed to remove"); }
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ))}
                {!members?.members?.length && <div className="text-xs text-slate-500">No members.</div>}
              </div>
            </>
          ) : (
            <div className="text-sm text-slate-500">Select a group to view members.</div>
          )}
        </div>
      </div>
    </div>
  );
}