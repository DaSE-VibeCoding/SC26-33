import { Copy, Bot, FileText, Send, Sparkles, TerminalSquare } from "lucide-react";
import { FormEvent, useState } from "react";
import { api, AgentResponse } from "../api";
import AgentTrace from "../components/AgentTrace";
import { AgentChartCard } from "../components/ChartCard";
import ResultTable from "../components/ResultTable";
import SqlBlock from "../components/SqlBlock";
import { useLayoutContext } from "../components/Layout";

const quickGroups = [
  { title: "学情诊断", items: ["这周哪些学生退步明显？", "生成一份本周班级学情报告。"] },
  { title: "风险预警", items: ["帮我找出需要重点辅导的学生。", "学习时长很高但正确率低的学生有哪些？"] },
  { title: "知识点分析", items: ["哪个知识点错误率最高？", "哪些学生在二次函数上掌握较弱？", "几何证明这个知识点在哪些班问题比较严重？"] },
  { title: "作业提交", items: ["七年级 3 班最近作业提交率怎么样？", "哪个班级风险学生最多？"] },
  { title: "班级报告", items: ["最近进步最大的学生是谁？"] },
];

function toneClass(mode: AgentResponse["mode"]) {
  if (mode === "llm") return "bg-emerald-50 text-emerald-700";
  if (mode === "template") return "bg-accent-50 text-accent-700";
  return "bg-amber-50 text-amber-700";
}

export default function DataAgent() {
  const { selectedClassId, systemMode } = useLayoutContext();
  const [question, setQuestion] = useState("这周哪些学生退步明显？");
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [developerMode, setDeveloperMode] = useState(false);

  async function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = await api.askAgent(question, selectedClassId, developerMode);
      setResult(payload);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const answer = result?.answer ?? {
    problem_understanding: "系统已接收教师问题。",
    analysis_task: "正在准备分析任务。",
    headline: "已生成分析结果",
    summary: "当前结果正在整理中。",
    key_findings: [],
    evidence: [],
    recommendations: [],
    follow_up_questions: [],
  };
  const table = result?.table ?? { columns: [], rows: [] };
  const chart = result?.chart ?? { type: "table" as const, title: "暂无图表", x_field: "none", y_field: null, series: [], data: [] };
  const debug = result?.debug ?? { sql: null, llm_used: false, model: null, reason: null };
  const trace = result?.trace ?? [];

  return (
    <div className="space-y-6">
      <section className="panel overflow-hidden">
        <div className="grid lg:grid-cols-[1.15fr,0.85fr]">
          <div className="soft-grid border-b border-slate-200 px-5 py-5 lg:border-b-0 lg:border-r lg:px-6">
            <div className="flex items-center gap-2 text-sm font-medium text-accent-600">
              <Bot size={16} />Natural Language Data Agent
            </div>
            <h3 className="mt-3 text-2xl font-semibold text-slate-950">像问教研助教一样提问，系统自动返回数据证据与教学建议</h3>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
              高频问题优先走稳定模板链路，未知问题在有 API Key 时启用 DeepSeek 在线增强。前端默认不展示 SQL，开发者模式可查看调试信息。
            </p>

            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm leading-6 outline-none transition focus:border-accent-500"
                placeholder="例如：七年级 3 班最近作业提交率怎么样？"
              />
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex h-11 items-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Send size={16} />
                  {loading ? "正在分析..." : "开始分析"}
                </button>
                <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={developerMode}
                    onChange={(event) => setDeveloperMode(event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-accent-600 focus:ring-accent-500"
                  />
                  开发者模式
                </label>
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${systemMode.mode === "online" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                  {systemMode.label}
                </span>
              </div>
            </form>
          </div>

          <div className="px-5 py-5 lg:px-6">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
              <Sparkles size={16} />快捷问题
            </div>
            <div className="mt-4 space-y-4">
              {quickGroups.map((group) => (
                <div key={group.title}>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{group.title}</p>
                  <div className="flex flex-wrap gap-2">
                    {group.items.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => setQuestion(item)}
                        className="rounded-full border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-600 transition hover:border-accent-300 hover:bg-accent-50 hover:text-accent-700"
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {error && <div className="panel p-5 text-sm text-rose-600">{error}</div>}

      {result ? (
        <div className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-[0.9fr,1.1fr]">
            <AgentTrace trace={trace} />
            <div className="panel p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${toneClass(result.mode)}`}>
                    {result.mode === "llm" ? "DeepSeek 在线增强" : result.mode === "template" ? "稳定模板链路" : "结果兜底"}
                  </div>
                  <h3 className="mt-3 text-xl font-semibold text-slate-950">{answer.headline}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-700">{answer.summary}</p>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    await navigator.clipboard.writeText(answer.summary);
                    setCopiedSummary(true);
                    window.setTimeout(() => setCopiedSummary(false), 1200);
                  }}
                  className="inline-flex h-10 shrink-0 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm text-slate-600 transition hover:bg-slate-50"
                >
                  <Copy size={16} />
                  {copiedSummary ? "已复制" : "复制总结"}
                </button>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                  <p className="text-xs text-slate-500">问题理解</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{answer.problem_understanding}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                  <p className="text-xs text-slate-500">分析任务</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{answer.analysis_task}</p>
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-3">
                {answer.evidence.map((item) => (
                  <div key={item.label} className="rounded-lg border border-slate-200 bg-white px-4 py-4">
                    <p className="text-xs text-slate-500">{item.label}</p>
                    <p className="mt-2 text-lg font-semibold text-slate-900">{item.value}</p>
                    {item.change && <p className="mt-1 text-xs text-slate-500">{item.change}</p>}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
            <div className="panel p-5">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <FileText size={16} />关键发现
              </div>
              <div className="mt-4 space-y-3">
                {answer.key_findings.map((item) => (
                  <div key={item} className="rounded-lg bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
                    {item}
                  </div>
                ))}
              </div>
            </div>
            <div className="panel p-5">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <Sparkles size={16} />建议动作
              </div>
              <div className="mt-4 space-y-3">
                {answer.recommendations.map((item) => (
                  <div key={item} className="rounded-lg bg-accent-50 px-4 py-3 text-sm leading-6 text-slate-700">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <AgentChartCard chart={chart} />

          <section>
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-slate-950">数据证据</h3>
              <p className="mt-1 text-sm text-slate-500">系统已返回对应的明细结果，支持教师继续下钻分析</p>
            </div>
            <ResultTable columns={table.columns} rows={table.rows} />
          </section>

          <section className="panel p-5">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <Sparkles size={16} />下一步可追问
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {answer.follow_up_questions.map((item) => (
                  <button
                    key={item}
                    type="button"
                  onClick={() => setQuestion(item)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 transition hover:border-accent-300 hover:bg-accent-50 hover:text-accent-700"
                >
                  {item}
                </button>
              ))}
            </div>
          </section>

          {developerMode && (
            <section className="space-y-4">
              <div className="panel p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
                  <TerminalSquare size={16} />调试信息
                </div>
                <pre className="overflow-x-auto rounded-lg bg-slate-950 px-4 py-4 text-xs leading-6 text-slate-100">
                  {JSON.stringify(debug, null, 2)}
                </pre>
              </div>
              {debug.sql && <SqlBlock sql={debug.sql} />}
            </section>
          )}
        </div>
      ) : (
        <div className="panel p-6 text-sm leading-6 text-slate-500">
          选择一个快捷问题，或直接输入教师关心的学情问题。系统会自动展示问题理解、分析任务、关键发现、图表证据与教学建议。
        </div>
      )}
    </div>
  );
}
