// frontend/src/features/dashboard/Dashboard.tsx

import React, { useState } from "react";
import KpiCard from "../../components/KpiCard";
import PrinterDetailModal from "../printers/PrinterDetailModal";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";
import { fetchAllAD } from "../../lib/api/fetchAllAD";

export default function Dashboard() {
  const [selectedPrinter, setSelectedPrinter] = useState(null);

  // -----------------------------
  // Backend queries
  // -----------------------------
  const servers = useQuery({
    queryKey: ["servers"],
    queryFn: () => api.get("/servers").then((r) => r.data),
  });

  const alerts = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api.get("/alerts").then((r) => r.data),
  });

  const vpnSessions = useQuery({
    queryKey: ["vpnSessions"],
    queryFn: () => api.get("/vpn/sessions").then((r) => r.data),
    refetchInterval: 5000,
  });

  const printers = useQuery({
    queryKey: ["printers"],
    queryFn: () => api.get("/printers").then((r) => r.data),
  });

  const adUsers = useQuery({
    queryKey: ["adUsers"],
    queryFn: () => fetchAllAD("/ad/users"),
  });

  const adGroups = useQuery({
    queryKey: ["adGroups"],
    queryFn: () => fetchAllAD("/ad/groups"),
  });

  const adComputers = useQuery({
    queryKey: ["adComputers"],
    queryFn: () => fetchAllAD("/ad/computers"),
  });

  // -----------------------------
  // Toner Parser — UTAX/Kyocera Final Version
  // -----------------------------
  const getTonerFromSupplies = (supplies) => {
    if (!supplies || supplies.length === 0) return null;

    const toner = { C: null, M: null, Y: null, K: null };

    for (const s of supplies) {
      const desc = (s.description || "").toUpperCase();
      const pct = s.percent;
      if (pct == null) continue;

      // UTAX always ends colour descriptions with a trailing " C/M/Y/K"
      if (desc.endsWith(" C")) { toner.C = pct; continue; }
      if (desc.endsWith(" M")) { toner.M = pct; continue; }
      if (desc.endsWith(" Y")) { toner.Y = pct; continue; }
      if (desc.endsWith(" K")) { toner.K = pct; continue; }

      // Generic fallback
      if (desc.includes("CYAN")) { toner.C = pct; continue; }
      if (desc.includes("MAGENTA")) { toner.M = pct; continue; }
      if (desc.includes("YELLOW")) { toner.Y = pct; continue; }
      if (desc.includes("BLACK")) { toner.K = pct; continue; }
    }

    // Mono detection
    const hasColour = toner.C || toner.M || toner.Y;
    if (!hasColour) return { K: toner.K };

    return toner;
  };

  // -----------------------------
  // Fetch printer detail snapshots
  // -----------------------------
  const printersBasic = printers.data ?? [];

  const printersDetailed = useQuery({
    queryKey: ["printers-detailed-dashboard"],
    enabled: printersBasic.length > 0,
    queryFn: async () => {
      const result = await Promise.all(
        printersBasic.map((p) =>
          api.get(`/printers/${p.id}`).then((res) => ({
            ...p,
            supplies: res.data.supplies,
            toner: getTonerFromSupplies(res.data.supplies),
          }))
        )
      );
      return result;
    },
  }).data ?? [];

  // -----------------------------
  // VPN Duration Formatter (Option C)
  // -----------------------------
  const formatDurationLong = (seconds) => {
    if (!seconds || seconds < 0) return "Connected for 0 minutes";

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0)
      return `Connected for ${hours} hour${hours > 1 ? "s" : ""}, ${minutes} minute${minutes !== 1 ? "s" : ""}`;

    return `Connected for ${minutes} minute${minutes !== 1 ? "s" : ""}`;
  };

  const vpnList = vpnSessions.data?.connected ?? [];

  // -----------------------------
  // KPI Metrics
  // -----------------------------
  const serversCount = servers.data?.length ?? 0;
  const alertCount = alerts.data?.length ?? 0;
  const vpnCount = vpnList.length;
  const printersCount = printersBasic.length;

  const adUsersTotal = adUsers.data?.length ?? 0;
  const adUsersLocked = adUsers.data?.filter((u) => u.locked)?.length ?? 0;
  const adGroupsTotal = adGroups.data?.length ?? 0;
  const adComputersTotal = adComputers.data?.length ?? 0;

  const tonerColours = {
    C: "#00b7ff",
    M: "#ff2fb2",
    Y: "#ffd600",
    K: "#666666",
  };

  return (
    <div className="space-y-6">

      {/* KPI CARDS */}
      <div className="grid grid-cols-4 gap-4">

        <Link to="/servers">
          <KpiCard label="Servers" value={serversCount} subtitle="Total Servers" />
        </Link>

        <Link to="/alerts">
          <KpiCard label="Alerts" value={alertCount} subtitle="Active Alerts" />
        </Link>

        <Link to="/vpn/sessions">
          <KpiCard label="VPN Sessions" value={vpnCount} subtitle="Active Users" />
        </Link>

        <Link to="/printers">
          <KpiCard label="Printers" value={printersCount} subtitle="Fleet Overview" />
        </Link>

        <Link to="/ad/users">
          <KpiCard
            label="AD Users"
            value={adUsersTotal}
            subtitle={`${adUsersLocked} locked`}
          />
        </Link>

        <Link to="/ad/groups">
          <KpiCard label="AD Groups" value={adGroupsTotal} subtitle="Directory Groups" />
        </Link>

        <Link to="/ad/computers">
          <KpiCard
            label="AD Computers"
            value={adComputersTotal}
            subtitle="AD Joined Devices"
          />
        </Link>

      </div>

      {/* PRINTERS + VPN PANELS */}
      <div className="grid grid-cols-2 gap-6">

        {/* PRINTER OVERVIEW */}
        <div className="card p-4 rounded-lg">
          <h2 className="text-lg mb-3">Printer Overview</h2>

          <div className="grid grid-cols-2 gap-4">
            {printersDetailed.map((p) => {
              const toner = p.toner;
              const keys = toner ? Object.keys(toner) : [];

              return (
                <div
                  key={p.id}
                  className="card p-3 rounded hover:shadow cursor-pointer"
                  onClick={() => setSelectedPrinter(p)}
                >
                  <div className="font-medium">{p.friendlyName || p.name}</div>
                  <div className="text-xs text-slate-500 dark:text-[var(--text-muted)]">
                    {p.status}
                  </div>

                  {!toner && (
                    <div className="mt-2 text-xs italic">No toner data</div>
                  )}

                  {toner && (
                    <div className="mt-2 space-y-2">
                      {keys.map((t) => (
                        <div key={t}>
                          <div className="flex justify-between text-xs">
                            <span>{t}</span>
                            <span>{toner[t]}%</span>
                          </div>

                          <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded">
                            <div
                              className="h-2 rounded"
                              style={{
                                width: `${toner[t]}%`,
                                backgroundColor: tonerColours[t],
                              }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* VPN PANEL */}
        <div className="card p-4 rounded-lg">
          <h2 className="text-lg mb-3">VPN – Connected Users</h2>

          {vpnCount === 0 && (
            <div className="text-sm text-slate-500">No VPN sessions active</div>
          )}

          {vpnList.slice(0, 10).map((u, i) => (
            <div key={i} className="flex justify-between text-sm py-1">
              <div className="flex flex-col">
                <span className="font-medium">{u.Username}</span>
                <span className="text-slate-500 dark:text-[var(--text-muted)]">
                  {formatDurationLong(u.ConnectionDuration?.Seconds ?? 0)}
                </span>
              </div>

              <span className="text-slate-500 dark:text-[var(--text-muted)]">
                {u.ClientIPv4Address}
              </span>
            </div>
          ))}

        </div>

      </div>

      {/* PRINTER MODAL */}
      {selectedPrinter && (
        <PrinterDetailModal
          printer={selectedPrinter}
          onClose={() => setSelectedPrinter(null)}
        />
      )}

    </div>
  );
}