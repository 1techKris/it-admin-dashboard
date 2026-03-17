import { useEffect, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";

type ADSettings = {
  server: string;
  user: string;
  password: string | null; // server never returns real password; this is always null
  base_dn: string;
  use_ssl: boolean;
  page_size: number;
};

export default function SettingsPage() {
  const [ad, setAd] = useState<ADSettings>({
    server: "",
    user: "",
    password: null,
    base_dn: "",
    use_ssl: false,
    page_size: 200,
  });

  const [newPwd, setNewPwd] = useState(""); // only sent if you fill it

  useEffect(() => {
    (async () => {
      const { data } = await api.get(endpoints.settings.adGet);
      setAd({
        server: data.server || "",
        user: data.user || "",
        password: null, // masked on GET
        base_dn: data.base_dn || "",
        use_ssl: !!data.use_ssl,
        page_size: Number(data.page_size || 200),
      });
    })();
  }, []);

  async function save() {
    try {
      const body: any = {
        server: ad.server,
        user: ad.user,
        base_dn: ad.base_dn,
        use_ssl: ad.use_ssl,
        page_size: ad.page_size,
      };
      if (newPwd) body.password = newPwd; // only update if provided
      await api.put(endpoints.settings.adPut, body);
      alert("Saved");
      setNewPwd("");
    } catch (e) {
      console.error(e);
      alert("Save failed");
    }
  }

  async function testBind() {
    try {
      const body: any = {
        server: ad.server,
        user: ad.user,
        base_dn: ad.base_dn,
        use_ssl: ad.use_ssl,
        page_size: ad.page_size,
      };
      if (newPwd) body.password = newPwd;
      await api.post(endpoints.settings.adTest, body);
      alert("Bind OK");
    } catch (e: any) {
      console.error(e);
      alert(`Bind failed: ${e?.response?.data?.detail || "Unknown error"}`);
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="text-lg font-semibold">Settings</h2>

      {/* Active Directory */}
      <div className="border rounded-2xl p-4 bg-white dark:bg-slate-800">
        <div className="text-sm font-semibold mb-3">Active Directory</div>

        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-slate-500">Server (e.g., ldap://dc1.local)</label>
            <input
              className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
              value={ad.server}
              onChange={(e) => setAd({ ...ad, server: e.target.value })}
            />
          </div>

          <div>
            <label className="text-xs text-slate-500">Base DN</label>
            <input
              className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
              value={ad.base_dn}
              onChange={(e) => setAd({ ...ad, base_dn: e.target.value })}
              placeholder="DC=yourdomain,DC=local"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500">Bind User</label>
            <input
              className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
              value={ad.user}
              onChange={(e) => setAd({ ...ad, user: e.target.value })}
              placeholder="YOURDOMAIN\\svc_ldap"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500">New Password (leave blank to keep existing)</label>
            <input
              className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
              type="password"
              value={newPwd}
              onChange={(e) => setNewPwd(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={ad.use_ssl}
              onChange={(e) => setAd({ ...ad, use_ssl: e.target.checked })}
            />
            <label className="text-xs text-slate-500">Use SSL (LDAPS)</label>
          </div>

          <div>
            <label className="text-xs text-slate-500">Page size</label>
            <input
              className="w-full border rounded px-3 py-2 dark:bg-slate-700 dark:border-slate-600"
              type="number"
              min={50}
              max={2000}
              value={ad.page_size}
              onChange={(e) => setAd({ ...ad, page_size: Number(e.target.value || 200) })}
            />
          </div>
        </div>

        <div className="flex gap-2 mt-3">
          <button
            onClick={save}
            className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Save
          </button>
          <button
            onClick={testBind}
            className="px-3 py-2 border rounded hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Test connection
          </button>
        </div>
      </div>
    </div>
  );
}