// frontend/src/components/toast/ToastProvider.tsx
import React, { createContext, useContext, useState } from "react";

const ToastContext = createContext<any>(null);

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: any) {
  const [toasts, setToasts] = useState<any[]>([]);

  const push = (msg: string) => {
    const id = Math.random().toString(36);
    setToasts((t) => [...t, { id, msg }]);
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 6000);
  };

  return (
    <ToastContext.Provider value={{ push }}>
      {children}

      <div className="fixed right-4 bottom-4 z-50 space-y-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="px-4 py-2 bg-slate-800 text-white rounded shadow"
          >
            {t.msg}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}