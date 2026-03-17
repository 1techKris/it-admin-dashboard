import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./layout/Layout";

import Dashboard from "./features/dashboard/Dashboard";
import Devices from "./features/servers/Servers";
import Printers from "./features/printers/Printers";
import Network from "./features/network/NetworkScan";

import ADUsers from "./features/ad/ADUsers";
import ADGroups from "./features/ad/ADGroups";
import ADComputers from "./features/ad/ADComputers";

import SettingsAD from "./features/settings/SettingsAD";
import SettingsVPN from "./features/settings/SettingsVPN";

import VPNSessions from "./features/vpn/VPNSessions";
import VPNHistory from "./features/vpn/VPNHistory";
import VPNAlerts from "./features/vpn/VPNAlerts";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />

          <Route path="/servers" element={<Devices />} />
          <Route path="/printers" element={<Printers />} />
          <Route path="/network" element={<Network />} />

          <Route path="/ad/users" element={<ADUsers />} />
          <Route path="/ad/groups" element={<ADGroups />} />
          <Route path="/ad/computers" element={<ADComputers />} />

          <Route path="/vpn/sessions" element={<VPNSessions />} />
          <Route path="/vpn/history" element={<VPNHistory />} />
          <Route path="/vpn/alerts" element={<VPNAlerts />} />

          <Route path="/settings/ad" element={<SettingsAD />} />
          <Route path="/settings/vpn" element={<SettingsVPN />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}