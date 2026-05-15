import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Layout from "./layout/Layout";
import Login from "./features/auth/Login";

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

import Switches from "./features/switches/Switches";
import SwitchDetails from "./features/switches/SwitchDetails";
import TopologyGraph from "./features/switches/TopologyGraph";
import TopologyAnalysis from "./features/switches/TopologyAnalysis";

import DeviceInventory from "./features/inventory/DeviceInventory";
import DeviceDetails from "./features/inventory/DeviceDetails";

import BCSessions from "./features/businesscentral/BCSessions";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* 🔐 Login route (NO layout) */}
        <Route path="/login" element={<Login />} />

        {/* 🔒 Authenticated app */}
        <Route
          path="/*"
          element={
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

                <Route path="/switches" element={<Switches />} />
                <Route path="/switches/:ip" element={<SwitchDetails />} />
                <Route path="/topology" element={<TopologyGraph />} />
                <Route path="/topology/analysis" element={<TopologyAnalysis />} />

                <Route path="/devices" element={<DeviceInventory />} />
                <Route path="/devices/:ip" element={<DeviceDetails />} />

                <Route
                  path="/business-central/sessions"
                  element={<BCSessions />}
                />
              </Routes>
            </Layout>
          }
        />

      </Routes>
    </BrowserRouter>
  );
}