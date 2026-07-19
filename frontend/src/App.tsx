import { useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api, ClassItem, SystemModeResponse } from "./api";
import { Layout, LayoutContext } from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import DataAgent from "./pages/DataAgent";
import Students from "./pages/Students";
import About from "./pages/About";

export default function App() {
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | undefined>(undefined);
  const [selectedWeeks, setSelectedWeeks] = useState<number>(8);
  const [systemMode, setSystemMode] = useState<SystemModeResponse>({
    mode: "offline",
    label: "离线演示模式",
    llm_available: false,
    model: null,
  });
  const [runtimeError, setRuntimeError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timers: number[] = [];

    const retryRequest = <T,>(request: () => Promise<T>, onSuccess: (value: T) => void, attempts = 12, delayMs = 1500) => {
      const run = (remainingAttempts: number) => {
        request()
          .then((value) => {
            if (!cancelled) {
              onSuccess(value);
            }
          })
          .catch(() => {
            if (cancelled || remainingAttempts <= 1) {
              return;
            }
            const timer = window.setTimeout(() => run(remainingAttempts - 1), delayMs);
            timers.push(timer);
          });
      };

      run(attempts);
    };

    retryRequest(() => api.getClasses(), setClasses, 10, 1200);
    retryRequest(() => api.getSystemMode(), setSystemMode, 15, 1200);

    return () => {
      cancelled = true;
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      setRuntimeError(event.message || "前端发生未知运行时错误。");
    };
    const handleRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      if (typeof reason === "string") {
        setRuntimeError(reason);
      } else if (reason && typeof reason.message === "string") {
        setRuntimeError(reason.message);
      } else {
        setRuntimeError("前端发生未处理的异步错误。");
      }
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);
    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, []);

  const contextValue = useMemo<LayoutContext>(
    () => ({
      classes,
      selectedClassId,
      setSelectedClassId,
      selectedWeeks,
      setSelectedWeeks,
      systemMode,
    }),
    [classes, selectedClassId, selectedWeeks, systemMode],
  );

  return (
    <>
      {runtimeError && (
        <div className="fixed inset-x-4 top-4 z-50 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-lg lg:left-[320px] lg:right-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-semibold">前端运行时错误</p>
              <p className="mt-1 break-all">{runtimeError}</p>
            </div>
            <button type="button" onClick={() => setRuntimeError(null)} className="rounded border border-rose-200 bg-white px-2 py-1 text-xs text-rose-700">
              关闭
            </button>
          </div>
        </div>
      )}
      <Routes>
        <Route element={<Layout context={contextValue} />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/agent" element={<DataAgent />} />
          <Route path="/students" element={<Students />} />
          <Route path="/about" element={<About />} />
        </Route>
      </Routes>
    </>
  );
}
