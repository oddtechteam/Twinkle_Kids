"use client";

import { CircleCheck, Info, TriangleAlert, X } from "lucide-react";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useRef, useState } from "react";

import styles from "./Toast.module.css";

type Tone = "success" | "info" | "warning";

interface ToastItem {
  id: number;
  title: string;
  description?: string;
  tone: Tone;
}

interface ToastApi {
  show: (toast: { title: string; description?: string; tone?: Tone }) => void;
}

const ToastContext = createContext<ToastApi | null>(null);
const ICONS = { success: CircleCheck, info: Info, warning: TriangleAlert };
const DURATION_MS = 4500;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((list) => list.filter((t) => t.id !== id));
  }, []);

  const show = useCallback<ToastApi["show"]>(
    ({ title, description, tone = "success" }) => {
      const id = nextId.current++;
      setToasts((list) => [...list.slice(-2), { id, title, description, tone }]);
      window.setTimeout(() => dismiss(id), DURATION_MS);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className={styles.region} role="status" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => {
          const Icon = ICONS[toast.tone];
          return (
            <div key={toast.id} className={`${styles.toast} ${styles[toast.tone]}`}>
              <Icon aria-hidden="true" size={20} className={styles.icon} />
              <div className={styles.text}>
                <p className={styles.title}>{toast.title}</p>
                {toast.description && <p className={styles.description}>{toast.description}</p>}
              </div>
              <button
                type="button"
                className={styles.close}
                onClick={() => dismiss(toast.id)}
                aria-label="Dismiss notification"
              >
                <X aria-hidden="true" size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (!api) throw new Error("useToast must be used inside <ToastProvider>");
  return api;
}
