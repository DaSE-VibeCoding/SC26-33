import { Bot, Database, LayoutDashboard, ShieldCheck, Sparkles, Workflow } from "lucide-react";

const cards = [
  { title: "系统目标", icon: Sparkles, content: "帮助教师通过自然语言快速查看班级趋势、知识点薄弱项和高风险学生名单。" },
  { title: "Agent 服务", icon: Bot, content: "常见问题走稳定模板链路，未知问题在有 Key 时由 DeepSeek 增强理解和 Text-to-SQL。" },
  { title: "安全机制", icon: ShieldCheck, content: "所有查询都经过 SQL 安全校验，只允许单条 SELECT / WITH 只读查询。" },
  { title: "学习分析", icon: LayoutDashboard, content: "围绕正确率、提交率、风险分、知识点掌握和学生画像生成可解释结果。" },
  { title: "数据底座", icon: Database, content: "SQLite 内置 6 个班级、约 240 名学生、12 个知识点和 8 周学习记录。" },
  { title: "工作流", icon: Workflow, content: "教师提问 → Agent 理解 → 数据查询 → 关键指标计算 → 图表解释 → 教学建议。" },
];

const flow = ["教师问题", "Agent 理解", "数据查询", "学习分析", "图表解释", "教学建议"];

export default function About() {
  return (
    <div className="space-y-6">
      <section className="panel p-6">
        <p className="text-xs uppercase tracking-wide text-accent-600">System Demo / About</p>
        <h3 className="mt-3 text-2xl font-semibold text-slate-950">EduInsight：面向教师的自然语言学情分析 Data Agent</h3>
        <p className="mt-4 max-w-4xl text-sm leading-7 text-slate-600">
          系统采用“稳定模板链路 + LLM Text-to-SQL 增强链路”的混合方案，在保证课堂演示稳定性的同时，保留对未知自然语言问题的扩展能力。教师端默认不展示 SQL，而是展示问题理解、关键发现、数据证据与教学建议。
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map(({ title, icon: Icon, content }) => (
          <div key={title} className="panel p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-50 text-accent-600">
              <Icon size={18} />
            </div>
            <h4 className="mt-4 text-base font-semibold text-slate-950">{title}</h4>
            <p className="mt-2 text-sm leading-6 text-slate-600">{content}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr,1fr]">
        <div className="panel p-6">
          <h3 className="panel-title">系统架构流程</h3>
          <div className="mt-5 grid gap-3">
            {flow.map((item, index) => (
              <div key={item} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-sm font-semibold text-accent-600">{index + 1}</div>
                <p className="text-sm text-slate-700">{item}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="panel p-6">
          <h3 className="panel-title">推荐演示顺序</h3>
          <ol className="mt-5 space-y-3 text-sm leading-6 text-slate-600">
            <li>1. 先在 Dashboard 展示整体学情概览、趋势图和风险学生榜。</li>
            <li>2. 切到 Data Agent，点击快捷问题展示 Agent 执行轨迹与关键发现。</li>
            <li>3. 选择“七年级 3 班最近作业提交率怎么样？”展示班级上下文理解与筛选联动。</li>
            <li>4. 进入学生画像页查看个体趋势、风险标签和个性化建议。</li>
            <li>5. 最后开启开发者模式，展示后端保留的调试信息与可选 SQL 视图。</li>
          </ol>
        </div>
      </section>
    </div>
  );
}
