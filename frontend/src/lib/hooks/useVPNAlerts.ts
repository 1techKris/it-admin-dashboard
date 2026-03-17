// frontend/src/lib/hooks/useVPNAlerts.ts

import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api/client";
import { useToast } from "../../components/toast/ToastProvider";

export default function useVPNAlerts() {
  const toast = useToast();

  return useQuery({
    queryKey: ["vpn-alert-poll"],
    queryFn: async () =>
      (await api.get("/vpn/alerts/live")).data, // add in backend
    refetchInterval: 5000,
    onSuccess(alerts) {
      if (Array.isArray(alerts)) {
        alerts.forEach((a) => {
          toast.push(`VPN Alert: ${a.username} just connected`);
        });
      }
    },
  });
}