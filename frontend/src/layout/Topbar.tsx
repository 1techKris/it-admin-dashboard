import { Search, RefreshCw, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export default function Topbar() {
  const [dark, setDark] = useState(false);

  // Remove inherited dark mode on first load
  useEffect(() => {
    document.documentElement.classList.remove("dark");
  }, []);

  // Toggle dark mode correctly
  useEffect(() => {
    if (dark) document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
  }, [dark]);

  return (
    <div className="sticky top-0 z-10 bg-white/80 dark:bg-slate-800 backdrop-blur border-b border-slate-200 dark:border-slate-700 px-4 py-2 flex items-center gap-3">
      <Search size={18} className="text-slate-500 dark:text-slate-400" />

      <input
        placeholder="Search devices, users, alerts…"
        className="h-8 px-3 border rounded w-64 text-sm dark:bg-slate-700 dark:border-slate-600 dark:text-white"
      />

      <div className="ml-auto flex items-center gap-2">
        <button className="border px-2 py-1 rounded flex items-center gap-1 text-sm hover:bg-slate-50 dark:hover:bg-slate-700 dark:border-slate-600">
          <RefreshCw size={14} /> Refresh
        </button>

        <button
          onClick={() => setDark(!dark)}
          className="border px-2 py-1 rounded text-sm hover:bg-slate-50 dark:hover:bg-slate-700 dark:border-slate-600 flex items-center gap-1"
        >
          {dark ? <Sun size={14} /> : <Moon size={14} />}
          {dark ? "Light" : "Dark"}
        </button>

        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600" />
      </div>
    </div>
  );
}