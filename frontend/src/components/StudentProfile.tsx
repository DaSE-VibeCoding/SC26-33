import ChartCard from "./ChartCard";
import ResultTable from "./ResultTable";
import { StudentProfileResponse } from "../api";

export default function StudentProfile({ data }: { data: StudentProfileResponse }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <section className="panel p-5">
          <p className="text-xs uppercase tracking-wide text-accent-600">Student Profile</p>
          <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 className="text-2xl font-semibold text-slate-950">{data.profile.name}</h3>
              <p className="mt-2 text-sm text-slate-500">
                {data.profile.class_name} · {data.profile.gender} · 任课教师 {data.profile.teacher_name}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {data.profile.risk_tags.map((item) => (
                  <span key={item} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                    {item}
                  </span>
                ))}
              </div>
            </div>
            <div className="grid min-w-[220px] gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              <div className="flex items-center justify-between">
                <span>最近正确率</span>
                <strong>{data.profile.latest_accuracy}%</strong>
              </div>
              <div className="flex items-center justify-between">
                <span>最近提交率</span>
                <strong>{data.profile.latest_submission_rate}%</strong>
              </div>
              <div className="flex items-center justify-between">
                <span>近期变化</span>
                <strong>{data.profile.recent_change}%</strong>
              </div>
            </div>
          </div>
        </section>

        <section className="panel p-5">
          <h3 className="panel-title">教师建议</h3>
          <p className="mt-3 text-sm leading-7 text-slate-700">{data.insight}</p>
          <div className="mt-4 space-y-3">
            {data.recommendations.map((item) => (
              <div key={item} className="rounded-lg bg-accent-50 px-4 py-3 text-sm leading-6 text-slate-700">
                {item}
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <ChartCard
          title="最近 8 周正确率趋势"
          subtitle="观察学生近阶段掌握水平是否稳定"
          type="line"
          data={data.weekly_accuracy as Array<Record<string, string | number>>}
          xKey="week"
          yKey="平均正确率"
        />
        <ChartCard
          title="最近 8 周提交率趋势"
          subtitle="查看作业投入和完成稳定性"
          type="line"
          data={data.weekly_accuracy as Array<Record<string, string | number>>}
          xKey="week"
          yKey="提交率"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr,1.1fr]">
        <ResultTable columns={["knowledge_point", "accuracy"]} rows={data.weak_knowledge_points as Array<Record<string, string | number | null>>} dense />
        <ResultTable columns={["title", "week_index", "knowledge_point", "status", "correct_rate", "time_spent_minutes"]} rows={data.submission_summary as Array<Record<string, string | number | null>>} dense />
      </div>
    </div>
  );
}
