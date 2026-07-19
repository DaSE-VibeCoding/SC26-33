import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

export default function KpiCard({ label, value, delta, trend }: { label: string; value: string; delta?: string | null; trend: "up" | "down" | "flat" }) {
  const Icon = trend === "up" ? ArrowUpRight : trend === "down" ? ArrowDownRight : ArrowRight;
  const trendClass = trend === "up" ? "bg-emerald-50 text-emerald-600" : trend === "down" ? "bg-amber-50 text-amber-600" : "bg-slate-100 text-slate-500";
  return (
    <div className="panel overflow-hidden p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${trendClass}`}><Icon size={18} /></div>
      </div>
      <p className="mt-4 text-xs font-medium text-slate-500">{delta ?? "暂无变化说明"}</p>
    </div>
  );
}
