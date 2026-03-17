import React from "react";
import { createRoot } from "react-dom/client";

import "./index.css";

import App from "./App";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "./components/toast/ToastProvider";

const queryClient = new QueryClient();

const root = createRoot(document.getElementById("root")!);

root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <App />
      </ToastProvider>
    </QueryClientProvider>
  </React.StrictMode>
);