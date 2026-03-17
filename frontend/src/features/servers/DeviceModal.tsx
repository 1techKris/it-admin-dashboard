export default function DeviceModal({ device, onClose }: any) {
  if (!device) return null;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-96 shadow-xl">
        <h2 className="text-lg font-semibold mb-3">{device.device_id}</h2>

        <div className="text-sm text-slate-600 dark:text-slate-300 mb-4">
          <div>Type: {device.type}</div>
          <div>OS: {device.os}</div>
          <div>IP: {device.ip}</div>
          <div>CPU: {device.cpu}%</div>
          <div>Memory: {device.mem}%</div>
          <div>Status: {device.status}</div>
        </div>

        <button
          className="w-full mt-3 border px-3 py-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700"
          onClick={onClose}
        >
          Close
        </button>
      </div>
    </div>
  );
}