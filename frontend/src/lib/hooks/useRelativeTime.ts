// frontend/src/lib/hooks/useRelativeTime.ts

import { useEffect, useState } from "react";

function formatRelative(date: Date): string {
  const now = new Date().getTime();
  const diff = Math.floor((now - date.getTime()) / 1000);

  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function useRelativeTime(value?: string | null) {
  const [text, setText] = useState<string>("—");

  useEffect(() => {
    if (!value) return;
    const d = new Date(value);
    if (isNaN(d.getTime())) return;

    const update = () => setText(formatRelative(d));
    update();

    const id = setInterval(update, 30000);
    return () => clearInterval(id);
  }, [value]);

  return text;
}