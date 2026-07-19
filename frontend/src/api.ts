export type ClassItem = {
  id: number;
  name: string;
  grade: string;
  teacher_name: string;
  full_name: string;
  student_count: number;
};

export type SystemModeResponse = {
  mode: "online" | "offline";
  label: string;
  llm_available: boolean;
  model?: string | null;
};

export type DashboardResponse = {
  meta: { scope_label: string; student_count: number; weeks: number };
  kpis: Array<{ label: string; value: string; delta?: string | null; trend: "up" | "down" | "flat" }>;
  accuracy_trend: Array<Record<string, string | number>>;
  submission_trend: Array<Record<string, string | number>>;
  knowledge_mastery: Array<Record<string, string | number>>;
  risk_students: Array<Record<string, string | number>>;
};

export type AgentTraceStep = {
  step: string;
  status: "done" | "warning" | "error";
  detail: string;
};

export type AgentEvidence = {
  label: string;
  value: string;
  change?: string | null;
};

export type AgentChart = {
  type: "bar" | "line" | "table" | "pie";
  title: string;
  x_field: string;
  y_field?: string | null;
  series: string[];
  data: Array<Record<string, string | number | null>>;
};

export type AgentResponse = {
  mode: "llm" | "template" | "fallback";
  intent: string;
  question: string;
  answer: {
    problem_understanding: string;
    analysis_task: string;
    headline: string;
    summary: string;
    key_findings: string[];
    evidence: AgentEvidence[];
    recommendations: string[];
    follow_up_questions: string[];
  };
  trace: AgentTraceStep[];
  table: {
    columns: string[];
    rows: Array<Record<string, string | number | null>>;
  };
  chart: AgentChart;
  debug: {
    sql?: string | null;
    llm_used: boolean;
    model?: string | null;
    reason?: string | null;
  };
};

export type StudentListItem = {
  id: number;
  name: string;
  class_id: number;
  class_name: string;
  teacher_name: string;
};

export type StudentProfileResponse = {
  profile: {
    id: number;
    name: string;
    gender: string;
    class_id: number;
    class_name: string;
    teacher_name: string;
    latest_accuracy: number;
    latest_submission_rate: number;
    recent_change: number;
    risk_tags: string[];
  };
  weekly_accuracy: Array<Record<string, string | number>>;
  submission_summary: Array<Record<string, string | number>>;
  weak_knowledge_points: Array<Record<string, string | number>>;
  insight: string;
  recommendations: string[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(payload.detail ?? "请求失败");
  }
  return response.json() as Promise<T>;
}

function parseStudentCountFromKpis(kpis: Array<{ label?: string; value?: string }> | undefined): number {
  if (!kpis?.length) return 0;
  const matched = kpis.find((item) => {
    const label = String(item.label ?? "");
    return label.includes("人数") || label.includes("班级人数") || label.includes("学生数");
  });
  if (!matched?.value) return 0;
  const num = Number(String(matched.value).replace(/[^\d.]/g, ""));
  return Number.isFinite(num) ? num : 0;
}

function normalizeKnowledgeMastery(rows: Array<Record<string, string | number>> | undefined) {
  return (rows ?? []).map((row) => {
    if ("知识点正确率" in row) return row;
    if ("正确率" in row) return { ...row, 知识点正确率: row["正确率"] };
    return row;
  });
}

function normalizeSubmissionTrend(rows: Array<Record<string, string | number>> | undefined) {
  return (rows ?? []).map((row) => {
    if ("提交率" in row) return row;
    if ("作业提交率" in row) return { ...row, 提交率: row["作业提交率"] };
    return row;
  });
}

function normalizeDashboardResponse(payload: any, classId?: number, weeks = 8): DashboardResponse {
  const fallbackScope = classId ? `班级 ${classId}` : "全部班级";
  return {
    meta: {
      scope_label: payload?.meta?.scope_label ?? fallbackScope,
      student_count: Number(payload?.meta?.student_count ?? parseStudentCountFromKpis(payload?.kpis)),
      weeks: Number(payload?.meta?.weeks ?? weeks),
    },
    kpis: Array.isArray(payload?.kpis) ? payload.kpis : [],
    accuracy_trend: Array.isArray(payload?.accuracy_trend) ? payload.accuracy_trend : [],
    submission_trend: normalizeSubmissionTrend(payload?.submission_trend),
    knowledge_mastery: normalizeKnowledgeMastery(payload?.knowledge_mastery),
    risk_students: Array.isArray(payload?.risk_students) ? payload.risk_students : [],
  };
}

function buildHeadlineFromLegacy(payload: any): string {
  if (typeof payload?.headline === "string" && payload.headline.trim()) return payload.headline.trim();
  if (typeof payload?.summary === "string" && payload.summary.trim()) {
    const sentence = payload.summary.split(/[。.!?]/).find((item: string) => item.trim());
    if (sentence) return sentence.trim();
  }
  if (payload?.intent === "submission_rate") return "已生成提交率分析结果";
  if (payload?.intent === "weekly_report") return "已生成班级学情报告";
  if (payload?.intent === "weakest_knowledge") return "已生成知识点分析结果";
  if (payload?.intent === "at_risk_students") return "已生成高风险学生分析结果";
  return "已生成学情分析结果";
}

function buildLegacyEvidence(payload: any): AgentEvidence[] {
  const rows = Array.isArray(payload?.rows) ? payload.rows : [];
  if (!rows.length) return [{ label: "数据状态", value: "暂无结果", change: "当前查询未返回数据" }];
  const first = rows[0] ?? {};
  const evidence: AgentEvidence[] = [];
  if (first.student_name) evidence.push({ label: "代表学生", value: String(first.student_name) });
  if (first.knowledge_point) evidence.push({ label: "知识点", value: String(first.knowledge_point) });
  if (first.class_name) evidence.push({ label: "班级", value: String(first.class_name) });
  if (typeof first.risk_score !== "undefined") evidence.push({ label: "风险分", value: String(first.risk_score) });
  if (typeof first.submission_rate !== "undefined") evidence.push({ label: "提交率", value: `${first.submission_rate}%` });
  if (!evidence.length) evidence.push({ label: "结果条数", value: `${rows.length} 条` });
  return evidence.slice(0, 3);
}

function normalizeAgentResponse(payload: any): AgentResponse {
  if (payload?.answer && payload?.table && payload?.chart) {
    return payload as AgentResponse;
  }

  const mode: AgentResponse["mode"] = payload?.mode === "llm" || payload?.mode === "fallback" ? payload.mode : "template";
  const rows = Array.isArray(payload?.rows) ? payload.rows : [];
  const columns = Array.isArray(payload?.columns) ? payload.columns : [];
  const summary = typeof payload?.summary === "string" ? payload.summary : "系统已完成查询，但当前返回结果缺少标准化摘要。";
  const recommendations = Array.isArray(payload?.recommendations) ? payload.recommendations.map(String) : [];

  return {
    mode,
    intent: String(payload?.intent ?? "fallback"),
    question: String(payload?.question ?? ""),
    answer: {
      problem_understanding: payload?.trace?.[0]?.detail ?? "系统已接收教师问题并开始理解其查询目标。",
      analysis_task: payload?.trace?.[1]?.detail ?? "系统正在根据问题匹配分析任务。",
      headline: buildHeadlineFromLegacy(payload),
      summary,
      key_findings: summary ? [summary] : ["系统已生成分析结果。"],
      evidence: buildLegacyEvidence(payload),
      recommendations,
      follow_up_questions: [],
    },
    trace: Array.isArray(payload?.trace) ? payload.trace : [],
    table: {
      columns,
      rows,
    },
    chart: {
      type: payload?.chart?.type ?? "table",
      title: payload?.chart?.title ?? "分析图表",
      x_field: payload?.chart?.x_field ?? payload?.chart?.x ?? "label",
      y_field: payload?.chart?.y_field ?? payload?.chart?.y ?? null,
      series: Array.isArray(payload?.chart?.series) ? payload.chart.series : [],
      data: Array.isArray(payload?.chart?.data) ? payload.chart.data : rows,
    },
    debug: {
      sql: typeof payload?.sql === "string" ? payload.sql : null,
      llm_used: Boolean(payload?.debug?.llm_used),
      model: payload?.debug?.model ?? null,
      reason: payload?.debug?.reason ?? null,
    },
  };
}

export const api = {
  getSystemMode: () => request<SystemModeResponse>("/api/system/mode"),
  getClasses: () => request<ClassItem[]>("/api/classes"),
  getDashboard: async (classId?: number, weeks = 8) => {
    const payload = await request<any>(`/api/dashboard?weeks=${weeks}${classId ? `&class_id=${classId}` : ""}`);
    return normalizeDashboardResponse(payload, classId, weeks);
  },
  getStudents: (classId?: number) => request<StudentListItem[]>(`/api/students${classId ? `?class_id=${classId}` : ""}`),
  getStudentProfile: (studentId: number) => request<StudentProfileResponse>(`/api/students/${studentId}`),
  askAgent: async (question: string, classId?: number, developerMode = false) => {
    const payload = await request<any>("/api/agent/query", {
      method: "POST",
      body: JSON.stringify({ question, class_id: classId, developer_mode: developerMode }),
    });
    return normalizeAgentResponse(payload);
  },
  resetDemoData: () => request<{ status: string; message: string }>("/api/reset-demo-data", { method: "POST" }),
};