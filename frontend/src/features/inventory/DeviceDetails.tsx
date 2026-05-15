import { useEffect, useState } from "react";
import api from "../../lib/api/client";
import { endpoints } from "../../lib/api/endpoints";
import { useParams } from "react-router-dom";
import SwitchDetails from "../switches/SwitchDetails";

type DeviceInfo = {
  ip: string;
  device_class?: string;
  vendor?: string;
  model?: string;
  hostname?: string;
  os?: string;
};

export default function DeviceDetails() {
  const { ip } = useParams();
  const [device, setDevice] = useState<DeviceInfo | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const res = await api.get(endpoints.network.deviceInfo(ip!));
      setDevice(res.data);
    } catch (err) {
      console.error(err);
      alert("Failed to load device");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (ip) load();
  }, [ip]);

  if (loading) return <div className="p-4">Loading device…</div>;
  if (!device) return <div className="p-4">Device not found.</div>;

  const cls = device.device_class || "Unknown";

  // SWITCH HANDLING — reuse full component
  if (cls.toLowerCase() === "switch") {
    return <SwitchDetails />;
  }

  return (
    <div className="grid gap-6 p-2">
      <h2 className="text-lg font-semibold">
        Device Details: <span className="font-mono">{ip}</span>
      </h2>

      <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
        <h3 className="font-semibold mb-2">Basic Info</h3>

        <div className="grid md:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-slate-500">Class</div>
            <div>{device.device_class}</div>
          </div>
          <div>
            <div className="text-slate-500">Vendor</div>
            <div>{device.vendor || "Unknown"}</div>
          </div>
          <div>
            <div className="text-slate-500">Model</div>
            <div>{device.model || "Unknown"}</div>
          </div>
          <div>
            <div className="text-slate-500">Hostname</div>
            <div>{device.hostname || "Unknown"}</div>
          </div>
          <div>
            <div className="text-slate-500">OS</div>
            <div>{device.os || "Unknown"}</div>
          </div>
        </div>
      </div>

      <div className="border rounded-xl p-4 bg-white dark:bg-slate-800">
        <h3 className="font-semibold">More information will appear here later…</h3>
        <div className="text-sm text-slate-400">
          (Firewall tables, router interfaces, camera RTSP paths, etc.)
        </div>
      </div>
    </div>
  );
}