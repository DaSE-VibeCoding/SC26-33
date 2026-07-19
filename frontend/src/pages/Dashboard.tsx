import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { api, DashboardResponse } from "../api";
import ChartCard from "../components/ChartCard";
import ErrorBoundary from "../components/ErrorBoundary";
import KpiCard from "../components/KpiCard";
import ResultTable from "../components/ResultTable";
import { useLayoutContext } from "../components/Layout";

export default function Dashboard() {
  const { selectedClassId, selectedWeeks, classes } = useLayoutContext();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api.getDashboard(selectedClassId, selectedWeeks).then(setData).catch((err: Error) => setError(err.message));
  }, [selectedClassId, selectedWeeks]);

  const currentClass = classes.find((item) => item.id === selectedClassId);

  if (error) return <div className="panel p-5 text-sm text-rose-600">{error}</div>;
  if (!data) return <div className="panel p-5 text-sm text-slate-500">正在加载班级学情数据...</div>;

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-lg bg-gradient-to-r from-slate-950 via-slate-900 to-accent-700 p-[1px] shadow-panel">
        <div className="rounded-lg bg-white px-6 py-6 lg:px-7 lg:py-7">
          <div className="grid gap-5 lg:grid-cols-[1.3fr,0.7fr] lg:items-end">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-accent-600">Dashboard Overview</p>
              <h3 className="mt-3 text-3xl font-semibold text-slate-950">用自然语言理解班级学习数据，快速发现薄弱知识点与高风险学生</h3>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
                当前工作台将班级正确率、作业提交率、知识点掌握情况和高风险学生名单整合在一起，方便教师先看整体，再进入 Data Agent 深入追问。
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                <p className="text-xs text-slate-500">分析范围</p>
                <p className="mt-2 text-base font-semibold text-slate-900">{data.meta.scope_label}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                <p className="text-xs text-slate-500">学生规模</p>
                <p className="mt-2 text-base font-semibold text-slate-900">{data.meta.student_count} 人</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                <p className="text-xs text-slate-500">时间窗口</p>
                <p className="mt-2 text-base font-semibold text-slate-900">最近 {data.meta.weeks} 周</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                <p className="text-xs text-slate-500">任课教师</p>
                <p className="mt-2 text-base font-semibold text-slate-900">{currentClass?.teacher_name ?? "全部教师"}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {data.kpis.map((item) => (
          <KpiCard key={item.label} {...item} />
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <ErrorBoundary title="正确率趋势图加载失败">
          <ChartCard title="最近 8 周正确率趋势" subtitle="观察班级整体掌握水平变化" type="line" data={data.accuracy_trend as Array<Record<string, string | number>>} xKey="week" yKey="平均正确率" />
        </ErrorBoundary>
        <ErrorBoundary title="提交率趋势图加载失败">
          <ChartCard title="班级提交率趋势" subtitle="关注作业完成节奏是否稳定" type="line" data={data.submission_trend as Array<Record<string, string | number>>} xKey="week" yKey="提交率" />
        </ErrorBoundary>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr] xl:items-start">
        <ErrorBoundary title="知识点图表加载失败">
          <ChartCard
            title="知识点掌握分布"
            subtitle="正确率越低，越需要优先安排讲解和练习"
            type="bar"
            data={data.knowledge_mastery as Array<Record<string, string | number>>}
            xKey="knowledge_point"
            yKey="知识点正确率"
            panelClassName="h-[420px]"
            chartHeightClass="min-h-0 flex-1"
          />
        </ErrorBoundary>

        <ErrorBoundary title="风险学生榜加载失败">
          <div className="panel flex h-[420px] flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="panel-title">需要关注的学生</h3>
                <p className="panel-subtitle mt-1">系统已综合正确率、提交率和退步幅度进行排序</p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                <AlertTriangle size={14} />重点跟进
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              <div className="space-y-3 pr-1">
                {data.risk_students.map((item, index) => (
                  <div key={`${item.student_name}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{item.student_name} · {item.class_name}</p>
                        <p className="mt-1 text-xs text-slate-500">薄弱知识点：{item.weak_knowledge_point}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-slate-900">{item.latest_accuracy}%</p>
                        <p className="mt-1 text-xs text-amber-600">{item.delta_accuracy}%</p>
                      </div>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-600">{item.action}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </ErrorBoundary>
      </section>

      <section>
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-slate-950">风险学生明细</h3>
          <p className="mt-1 text-sm text-slate-500">支持后续在学生画像页继续查看个人趋势与辅导建议</p>
        </div>
        <ErrorBoundary title="风险学生表格加载失败">
          <ResultTable
            columns={["student_name", "class_name", "latest_accuracy", "delta_accuracy", "submission_rate", "weak_knowledge_point", "action"]}
            rows={data.risk_students as Array<Record<string, string | number | null>>}
            scrollHeightClass="h-[360px]"
          />
        </ErrorBoundary>
      </section>
    </div>
  );
}
