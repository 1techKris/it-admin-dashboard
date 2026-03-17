import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";

export default function ADVPNUsers() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["vpn-sessions"],
    queryFn: async () => (await api.get("/vpn/sessions")).data,
    refetchInterval: 5000, // refresh every 5 seconds
  });

  if (isLoading) return <div>Loading VPN connections...</div>;
  if (isError) return <div>Failed to load VPN sessions.</div>;

  return (
    <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
      <h3 className="font-semibold text-lg mb-3">Active VPN Connections</h3>

      <table className="w-full text-sm">
        <thead className="bg-slate-50 dark:bg-slate-700">
          <tr>
            <th className="p-2 text-left">User</th>
            <th className="p-2 text-left">IPv4</th>
            <th className="p-2 text-left">Duration</th>
            <th className="p-2 text-left">Connected Since</th>
          </tr>
        </thead>
        <tbody>
          {data.connected.map((s: any) => (
            <tr key={s.Username} className="border-t">
              <td className="p-2">{s.Username}</td>
              <td className="p-2">{s.ClientIPv4Address}</td>
              <td className="p-2">{s.ConnectionDuration}</td>
              <td className="p-2">{s.ConnectionStartTime}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}