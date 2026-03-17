// frontend/src/layout/Sidebar.tsx

import { Link, useLocation } from "react-router-dom";
import React from "react";

export default function Sidebar() {
  const loc = useLocation();

  const item = (to: string, label: string) => (
    <Link
      to={to}
      className={`block px-4 py-2 rounded hover:bg-slate-200 dark:hover:bg-slate-700 ${
        loc.pathname === to ? "bg-slate-300 dark:bg-slate-600" : ""
      }`}
    >
      {label}
    </Link>
  );

  return (
    <div className="w-56 bg-slate-100 dark:bg-slate-800 p-4 space-y-4 h-screen overflow-y-auto">

      <div>
        <div className="text-xs font-semibold text-slate-500 mb-1">Dashboard</div>
        {item("/", "Overview")}
      </div>

      <div>
        <div className="text-xs font-semibold text-slate-500 mb-1">Devices & Network</div>
        {item("/servers", "Servers")}
        {item("/printers", "Printers")}
        {item("/network", "Network Scanner")}
      </div>

      <div>
        <div className="text-xs font-semibold text-slate-500 mb-1">Active Directory</div>
        {item("/ad/users", "AD Users")}
        {item("/ad/groups", "AD Groups")}
        {item("/ad/computers", "AD Computers")}
      </div>

      <div>
        <div className="text-xs font-semibold text-slate-500 mb-1">VPN</div>
        {item("/vpn/sessions", "VPN Sessions")}
        {item("/vpn/history", "VPN History")}
        {item("/vpn/alerts", "VPN Alerts")}
        {item("/settings/vpn", "VPN Settings")}
      </div>

      <div>
        <div className="text-xs font-semibold text-slate-500 mb-1">Settings</div>
        {item("/settings", "General Settings")}
        {item("/settings/ad", "AD Settings")}
      </div>
    </div>
  );
}