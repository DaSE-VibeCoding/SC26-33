import { BarChart3, Bot, GraduationCap, LayoutDashboard, Sparkles, Users } from "lucide-react";
import { NavLink, Outlet, useLocation, useOutletContext } from "react-router-dom";
import { ClassItem, SystemModeResponse } from "../api";
import ErrorBoundary from "./ErrorBoundary";

export type LayoutContext = {
  classes: ClassItem[];
  selectedClassId?: number;
  setSelectedClassId: (value: number | undefined) => void;
  selectedWeeks: number;
  setSelectedWeeks: (value: number) => void;
  systemMode: SystemModeResponse;
};

type LayoutProps = { context: LayoutContext };

const navItems = [
  { to: "/dashboard", label: "班级概览", icon: LayoutDashboard },
  { to: "/agent", label: "Data Agent", icon: Bot },
  { to: "/students", label: "学生画像", icon: Users },
  { to: "/about", label: "系统说明", icon: BarChart3 },
];

export function Layout({ context }: LayoutProps) {
  const location = useLocation();
  const showWeekFilter = location.pathname === "/dashboard";
  const modeClass =
    context.systemMode.mode === "online"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : "bg-slate-100 text-slate-600 border-slate-200";

  return (
    <div className="h-[100dvh] overflow-hidden bg-slate-100 text-ink">
      <div className="mx-auto flex h-full max-w-[1600px] gap-6 p-4 lg:p-6">
        <aside className="hidden h-full w-[280px] shrink-0 rounded-lg bg-slate-950 px-5 py-6 text-slate-100 shadow-panel lg:flex lg:flex-col">
          <div className="mb-8 flex items-start gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gradient-to-br from-accent-500 via-accent-600 to-cyan-400 text-white">
              <GraduationCap size={22} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">EduInsight</h1>
              <p className="mt-1 text-xs leading-5 text-slate-400">教师侧自然语言学情分析 Data Agent</p>
            </div>
          </div>

          <nav className="space-y-2">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-4 py-3 text-sm transition ${
                    isActive ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
                  }`
                }
              >
                <Icon size={18} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto rounded-lg border border-white/10 bg-white/5 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Demo Focus</p>
            <p className="mt-2 text-sm leading-6 text-slate-200">
              用自然语言理解班级学习数据，快速发现薄弱知识点、高风险学生和教学干预机会。
            </p>
          </div>
        </aside>

        <main className="min-w-0 flex-1 overflow-hidden">
          <div className="flex h-full flex-col rounded-lg bg-gradient-to-r from-slate-950 via-slate-900 to-accent-700 p-[1px] shadow-panel">
            <div className="flex min-h-0 flex-1 flex-col rounded-lg bg-white">
              <header className="flex flex-col gap-5 border-b border-slate-200 px-5 py-5 lg:px-7">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="inline-flex items-center gap-2 rounded-full bg-accent-50 px-3 py-1 text-xs font-medium text-accent-700">
                      <Sparkles size={14} />
                      Teacher Analytics Workspace
                    </div>
                    <h2 className="mt-3 text-2xl font-semibold text-slate-950">让教师像提问一样理解学习数据</h2>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                      将班级作业、答题、学习行为与风险识别整合到一个可解释的学情分析工作台，既能稳定演示，也能体现真实 AI 数据助教的产品形态。
                    </p>
                  </div>
                  <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium ${modeClass}`}>
                    <Sparkles size={16} />
                    {context.systemMode.label}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-slate-600">班级范围</label>
                    <select
                      value={context.selectedClassId ?? ""}
                      onChange={(event) => context.setSelectedClassId(event.target.value ? Number(event.target.value) : undefined)}
                      className="h-11 min-w-[210px] rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm outline-none transition focus:border-accent-500 focus:bg-white"
                    >
                      <option value="">全部班级</option>
                      {context.classes.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.full_name} · {item.student_count} 人
                        </option>
                      ))}
                    </select>
                  </div>

                  {showWeekFilter && (
                    <div className="flex items-center gap-3">
                      <label className="text-sm font-medium text-slate-600">时间范围</label>
                      <select
                        value={context.selectedWeeks}
                        onChange={(event) => context.setSelectedWeeks(Number(event.target.value))}
                        className="h-11 min-w-[140px] rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm outline-none transition focus:border-accent-500 focus:bg-white"
                      >
                        <option value={4}>最近 4 周</option>
                        <option value={6}>最近 6 周</option>
                        <option value={8}>最近 8 周</option>
                      </select>
                    </div>
                  )}
                </div>
              </header>
              <div className="min-h-0 flex-1 overflow-y-auto p-5 lg:p-7">
                <ErrorBoundary title="当前页面加载失败">
                  <Outlet context={context} />
                </ErrorBoundary>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export function useLayoutContext() {
  return useOutletContext<LayoutContext>();
}
