const LABELS: Record<string, string> = {
  student_name: "学生",
  class_name: "班级",
  latest_accuracy: "最近正确率",
  delta_accuracy: "变化幅度",
  submission_rate: "提交率",
  weak_knowledge_point: "薄弱知识点",
  risk_score: "风险分",
  action: "建议动作",
  knowledge_point: "知识点",
  accuracy_rate: "正确率",
  accuracy: "正确率",
  error_rate: "错误率",
  record_count: "记录数",
  avg_duration: "平均学习时长",
  week_index: "周次",
  title: "作业名称",
  status: "状态",
  correct_rate: "正确率",
  time_spent_minutes: "用时",
  question_count: "题量",
  students_affected: "影响学生数",
  total_students: "学生总数",
  risk_students: "风险学生数",
  avg_risk_score: "平均风险分",
};

export default function ResultTable({
  columns,
  rows,
  dense = false,
  scrollHeightClass,
}: {
  columns: string[];
  rows: Array<Record<string, string | number | null>>;
  dense?: boolean;
  scrollHeightClass?: string;
}) {
  return (
    <div className="panel overflow-hidden">
      <div className={`overflow-auto ${scrollHeightClass ?? ""}`}>
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="sticky top-0 z-10 bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th key={column} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {LABELS[column] ?? column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map((row, index) => (
              <tr key={index} className="hover:bg-slate-50/70">
                {columns.map((column) => (
                  <td key={`${index}-${column}`} className={`px-4 text-sm text-slate-700 ${dense ? "py-2.5" : "py-3.5"}`}>
                    {row[column] ?? "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}