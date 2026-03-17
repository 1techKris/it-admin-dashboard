// frontend/src/features/vpn/VPNGeoIPBadge.tsx

export default function VPNGeoIPBadge({ geo }: { geo: any }) {
  if (!geo) return null;

  return (
    <div className="inline-block px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-xs mr-2">
      {geo.city && <span>{geo.city}, </span>}
      {geo.country && <span>{geo.country} </span>}
      {geo.isp && <span className="text-slate-500">({geo.isp})</span>}
    </div>
  );
}