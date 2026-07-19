import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { AgentTraceStep } from "../api";

export default function AgentTrace({ trace }: { trace: AgentTraceStep[] }) {
  return (
    <div className="panel p-5">
      <div className="mb-4">
        <h3 className="panel-title">Agent 执行轨迹</h3>
        <p className="panel-subtitle mt-1">展示系统从理解问题到生成建议的分析步骤。</p>
      </div>
      <div className="space-y-4">
        {trace.map((item, index) => {
          const warning = item.status !== "done";
          return (
            <div key={`${item.step}-${index}`} className="flex gap-4">
              <div className="flex w-7 flex-col items-center">
                <span className={`flex h-7 w-7 items-center justify-center rounded-full ${warning ? "bg-amber-50 text-amber-600" : "bg-accent-50 text-accent-600"}`}>
                  {warning ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
                </span>
                {index < trace.length - 1 && <span className="mt-1 h-full w-px bg-slate-200" />}
              </div>
              <div className="pb-4">
                <p className="text-sm font-semibold text-slate-900">{item.step}</p>
                <p className="mt-1 text-sm leading-6 text-slate-500">{item.detail}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
