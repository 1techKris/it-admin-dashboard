import React from "react";

export default function KpiCard({ label, value, subtitle }: any) {
  return (
    <div className="card p-4 rounded-lg flex flex-col">
      <div className="text-sm text-slate-500 dark:text-[var(--text-muted)]">
        {label}
      </div>
      <div className="text-3xl font-semibold text-slate-800 dark:text-[var(--text-primary)]">
        {value}
      </div>
      <div className="text-xs text-slate-400 dark:text-[var(--text-secondary)]">
        {subtitle}
      </div>
    </div>
  );
}