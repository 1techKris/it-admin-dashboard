import { Search, RefreshCw, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

// Import both logo variants
import logoLight from "../assets/logo_light.svg";
import logoDark from "../assets/logo_dark.svg";

export default function Topbar() {
  const [dark, setDark] = useState(true);

  // Remove inherited dark mode on first load
  useEffect(() => {
    document.documentElement.classList.remove("dark");
  }, []);

  // Apply dark mode + persist
  useEffect(() => {
    if (dark) document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");

    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  // Load stored theme
  useEffect(() => {
    const stored = localStorage.getItem("theme");
    if (stored === "dark") setDark(true);
    if (stored === "light") setDark(false);
  }, []);

  return (
    <div className="sticky top-0 z-10 bg-white/80 dark:bg-slate-800 backdrop-blur border-b border-slate-200 dark:border-slate-700 px-4 py-2 flex items-center gap-4">

      {/* LOGO + TITLE */}
      <div className="flex items-center gap-3">
        <img
          src={dark ? logoDark : logoLight}
          alt="Dashboard Logo"
          className="h-9 w-auto select-none"
        />

        <span className="text-lg font-semibold text-slate-700 dark:text-slate-100">
          IT Admin Dashboard
        </span>
      </div>

      {/* SEARCH BOX */}
      <div className="flex items-center gap-2 ml-6">
        <Search size={18} className="text-slate-500 dark:text-slate-400" />
        <input
          placeholder="Search devices, users, alerts…"
          className="h-8 px-3 border rounded w-64 text-sm 
                     bg-white dark:bg-slate-700 
                     border-slate-300 dark:border-slate-600 
                     text-slate-800 dark:text-white"
        />
      </div>

      {/* RIGHT SIDE BUTTONS */}
      <div className="ml-auto flex items-center gap-2">

        {/* REFRESH BUTTON */}
        <button
          className="border px-2 py-1 rounded flex items-center gap-1 text-sm
                     hover:bg-slate-50 dark:hover:bg-slate-700
                     border-slate-300 dark:border-slate-600"
        >
          <RefreshCw size={14} /> Refresh
        </button>

        {/* THEME TOGGLE */}
        <button
          onClick={() => setDark(!dark)}
          className="border px-2 py-1 rounded text-sm flex items-center gap-1
                     hover:bg-slate-50 dark:hover:bg-slate-700
                     border-slate-300 dark:border-slate-600"
        >
          {dark ? <Sun size={14} /> : <Moon size={14} />}
          {dark ? "Light" : "Dark"}
        </button>

      </div>
    </div>
  );
}
``