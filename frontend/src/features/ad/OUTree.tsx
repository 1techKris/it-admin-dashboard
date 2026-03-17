// frontend/src/features/ad/OUTree.tsx

import React from "react";

export type OUTreeNode = {
  type: "ou";
  name: string;
  dn: string;
  users: { name: string; sam: string; dn: string }[];
  children: OUTreeNode[];
};

export default function OUTree({
  data,
  expanded,
  toggle,
  onSelectOu,
  selectedOuDn,
  onDropUser,
}: {
  data: OUTreeNode | null;
  expanded: Set<string>;
  toggle: (dn: string, open?: boolean) => void;
  onSelectOu: (dn: string | null) => void;
  selectedOuDn: string | null;
  onDropUser: (userDn: string, targetOuDn: string) => void;
}) {
  if (!data) return <div className="text-sm text-slate-500">No OUs found.</div>;

  const Node: React.FC<{ node: OUTreeNode; depth?: number }> = ({ node, depth = 0 }) => {
    const isOpen = expanded.has(node.dn);

    const totalUsers = (n: OUTreeNode): number => {
      let t = n.users?.length || 0;
      for (const c of n.children || []) t += totalUsers(c);
      return t;
    };

    const total = totalUsers(node);

    return (
      <div className="select-none">
        <div
          className="flex items-center gap-2 py-1 cursor-pointer rounded-md"
          style={{ paddingLeft: `${Math.min(depth + 1, 6) * 8}px` }}
          onClick={() => toggle(node.dn)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            const userDn = e.dataTransfer.getData("userDN");
            if (userDn) onDropUser(userDn, node.dn);
          }}
          title={node.dn}
        >
          <span className="text-xs w-4 text-slate-500">
            {node.children?.length || node.users?.length ? (isOpen ? "▼" : "▶") : "•"}
          </span>
          <button
            className={`text-left flex-1 text-sm ${
              selectedOuDn === node.dn
                ? "font-semibold text-blue-600"
                : "text-slate-800 dark:text-slate-200"
            }`}
            onClick={(e) => {
              e.stopPropagation();
              onSelectOu(node.dn);
            }}
          >
            {node.name} <span className="text-xs text-slate-500">({total})</span>
          </button>
        </div>

        {isOpen && (
          <div>
            {node.users?.map((u) => (
              <div
                key={u.dn}
                className="flex items-center gap-2 py-1 pl-8"
                draggable
                onDragStart={(e) => e.dataTransfer.setData("userDN", u.dn)}
                title={u.dn}
              >
                <span className="text-xs w-4">👤</span>
                <span className="text-sm text-slate-700 dark:text-slate-300">{u.name}</span>
              </div>
            ))}
            {node.children?.map((c) => (
              <Node key={c.dn} node={c} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  return <Node node={data} />;
}