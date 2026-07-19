from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import pandas as pd

from .analytics_service import list_classes
from .db import get_connection
from .llm import generate_sql_plan, llm_settings, summarize_result
from .schemas import AgentAnswer, AgentResponse, ChartData, DebugInfo, EvidenceItem, TableData, TraceStep
from .sql_guard import validate_select_sql


KNOWLEDGE_POINTS = [
    "一次函数",
    "二次函数",
    "方程求解",
    "几何证明",
    "概率统计",
    "数据分析",
    "阅读理解",
    "写作表达",
    "词汇积累",
    "实验探究",
    "信息检索",
    "逻辑推理",
]

FOLLOW_UPS = {
    "declining_students": ["这些学生主要错在哪些知识点？", "能否生成一份重点辅导名单？"],
    "weakest_knowledge": ["这个知识点在哪些班问题最严重？", "哪些学生在这个知识点上最需要帮助？"],
    "at_risk_students": ["这些学生近两周的提交率如何？", "能否给出分层辅导建议？"],
    "weekly_report": ["能否只看七年级3班的周报？", "请给出下周教学重点。"],
    "submission_rate": ["提交率下降主要集中在哪些学生？", "最近缺交最严重的是哪个班？"],
    "knowledge_point_students": ["这些学生最近两周有改善吗？", "请生成针对该知识点的辅导建议。"],
    "high_effort_low_accuracy": ["这些学生主要薄弱在哪些知识点？", "能否给出学习方法调整建议？"],
    "improving_students": ["他们的进步主要来自哪些知识点？", "是否可以作为同伴示范对象？"],
    "class_most_risk": ["这个班的主要风险来自提交率还是正确率？", "请列出该班重点关注学生。"],
    "knowledge_class_issue": ["这个知识点在该班影响了哪些学生？", "请给出一次课内干预建议。"],
    "custom_sql": ["能否换一种角度继续分析？", "请只看某个班级的数据。"],
}

DANGEROUS_PATTERNS = [
    "drop",
    "delete",
    "truncate",
    "alter",
    "insert",
    "update",
    "删除",
    "清空",
    "删库",
    "销毁",
    "drop table",
]


@dataclass
class Plan:
    intent: str
    mode: str
    understand: str
    task: str
    sql: str
    chart_type: str
    chart_title: str
    x_field: str
    y_field: str | None
    series: list[str]
    reason: str = ""


def _run(sql: str) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn)


def _rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = df.to_dict(orient="records")
    for row in rows:
        for key, value in row.items():
            if isinstance(value, float):
                row[key] = round(value, 2)
    return rows


def _escape_sql(value: str) -> str:
    return value.replace("'", "''")


def _knowledge_point(question: str) -> str | None:
    for item in KNOWLEDGE_POINTS:
        if item in question:
            return item
    if "函数与方程" in question:
        return "函数与方程"
    return None


def _class_context(question: str, request_class_id: int | None = None) -> tuple[int | None, str | None]:
    classes = {int(item["id"]): item for item in list_classes()}
    if request_class_id in classes:
        item = classes[request_class_id]
        return request_class_id, str(item["full_name"])

    compact = re.sub(r"\s+", "", question)
    for item in classes.values():
        full_name = str(item["full_name"])
        if full_name.replace(" ", "") in compact:
            return int(item["id"]), full_name

    match = re.search(r"七年级\s*([1-6])\s*班", compact)
    if not match:
        match = re.search(r"([1-6])\s*班", compact)
    if match:
        class_id = int(match.group(1))
        if class_id in classes:
            return class_id, str(classes[class_id]["full_name"])
    return None, None


def _class_filter(class_id: int | None, alias: str = "s") -> str:
    return "1 = 1" if class_id is None else f"{alias}.class_id = {int(class_id)}"


def _is_dangerous(question: str) -> bool:
    lowered = question.lower()
    return any(pattern in lowered or pattern in question for pattern in DANGEROUS_PATTERNS)


def detect_template_intent(question: str) -> str | None:
    if any(word in question for word in ["报告", "周报", "总结", "学情报告", "班级报告"]):
        return "weekly_report"
    if any(word in question for word in ["学习时长", "花很多时间", "时长很高"]) and any(word in question for word in ["正确率低", "效果差", "成绩低"]):
        return "high_effort_low_accuracy"
    if any(word in question for word in ["进步最大", "进步明显", "提升最快", "最近进步"]):
        return "improving_students"
    if any(word in question for word in ["哪个班级风险学生最多", "风险学生最多", "哪个班风险最高"]):
        return "class_most_risk"
    if _knowledge_point(question) and any(word in question for word in ["哪些班", "哪个班", "问题严重", "问题比较严重"]):
        return "knowledge_class_issue"
    if any(word in question for word in ["提交率", "作业完成", "作业提交", "完成情况"]):
        return "submission_rate"
    if any(word in question for word in ["退步", "下降", "变差", "下滑", "退化"]):
        return "declining_students"
    if any(word in question for word in ["重点辅导", "高风险", "需要关注", "重点关注", "辅导名单"]):
        return "at_risk_students"
    if _knowledge_point(question) and any(word in question for word in ["掌握较弱", "较弱", "薄弱", "学得不好", "错误多"]):
        return "knowledge_point_students"
    if any(word in question for word in ["错误率最高", "薄弱知识点", "掌握不好", "正确率最低"]):
        return "weakest_knowledge"
    return None


def _closest_template_intent(question: str) -> str | None:
    if _knowledge_point(question):
        return "knowledge_point_students"
    if "班" in question and any(word in question for word in ["提交", "作业"]):
        return "submission_rate"
    if any(word in question for word in ["报告", "总结"]):
        return "weekly_report"
    return None

def _template_plan(intent: str, question: str, class_id: int | None, scope_label: str | None) -> Plan:
    student_condition = _class_filter(class_id, "st")
    scope_condition = _class_filter(class_id, "s")
    knowledge_point = _knowledge_point(question)
    scope_name = scope_label or "全部班级"

    if intent == "declining_students":
        sql = f"""
        WITH weekly AS (
            SELECT sub.student_id, a.week_index, AVG(COALESCE(sub.correct_rate, 0)) AS avg_accuracy
            FROM submissions sub
            JOIN assignments a ON a.id = sub.assignment_id
            JOIN students s ON s.id = sub.student_id
            WHERE {scope_condition}
            GROUP BY sub.student_id, a.week_index
        ),
        latest AS (
            SELECT student_id, avg_accuracy
            FROM weekly
            WHERE week_index = (SELECT MAX(week_index) FROM assignments)
        ),
        previous AS (
            SELECT student_id, AVG(avg_accuracy) AS previous_accuracy
            FROM weekly
            WHERE week_index < (SELECT MAX(week_index) FROM assignments)
            GROUP BY student_id
        ),
        weak_kp AS (
            SELECT q.student_id, kp.name AS weak_knowledge_point,
                   ROW_NUMBER() OVER (PARTITION BY q.student_id ORDER BY AVG(q.is_correct) ASC) AS rn
            FROM question_records q
            JOIN students s ON s.id = q.student_id
            JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
            WHERE {scope_condition}
            GROUP BY q.student_id, kp.name
        )
        SELECT st.id AS student_id, st.name AS student_name, c.grade || c.name AS class_name,
               ROUND(COALESCE(latest.avg_accuracy, 0) * 100, 1) AS latest_accuracy,
               ROUND((COALESCE(latest.avg_accuracy, 0) - COALESCE(previous.previous_accuracy, 0)) * 100, 1) AS delta_accuracy,
               weak_kp.weak_knowledge_point
        FROM students st
        JOIN classes c ON c.id = st.class_id
        LEFT JOIN latest ON latest.student_id = st.id
        LEFT JOIN previous ON previous.student_id = st.id
        LEFT JOIN weak_kp ON weak_kp.student_id = st.id AND weak_kp.rn = 1
        WHERE {student_condition}
        ORDER BY delta_accuracy ASC
        LIMIT 12
        """
        return Plan(intent, "template", "系统已识别出教师想找出最近一周退步明显的学生。", "对比最新周与前期平均正确率，定位下降幅度最大的学生。", sql, "bar", f"{scope_name}退步学生分布", "student_name", "delta_accuracy", [])

    if intent == "weakest_knowledge":
        sql = f"""
        SELECT kp.name AS knowledge_point,
               ROUND(AVG(q.is_correct) * 100, 1) AS accuracy_rate,
               ROUND((1 - AVG(q.is_correct)) * 100, 1) AS error_rate,
               COUNT(*) AS record_count
        FROM question_records q
        JOIN students s ON s.id = q.student_id
        JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
        WHERE {scope_condition}
        GROUP BY kp.id, kp.name
        ORDER BY error_rate DESC
        LIMIT 10
        """
        return Plan(intent, "template", "系统已识别出教师在追问整体最薄弱的知识点。", "统计各知识点正确率与错误率，找出当前最需要补强的主题。", sql, "bar", f"{scope_name}知识点薄弱度", "knowledge_point", "error_rate", [])

    if intent == "at_risk_students":
        sql = f"""
        WITH weekly AS (
            SELECT sub.student_id, a.week_index,
                   AVG(COALESCE(sub.correct_rate, 0)) AS avg_accuracy,
                   AVG(CASE WHEN sub.status = 'submitted' THEN 1.0 ELSE 0.0 END) AS submission_rate
            FROM submissions sub
            JOIN assignments a ON a.id = sub.assignment_id
            JOIN students s ON s.id = sub.student_id
            WHERE {scope_condition}
            GROUP BY sub.student_id, a.week_index
        ),
        latest AS (
            SELECT student_id, avg_accuracy, submission_rate
            FROM weekly
            WHERE week_index = (SELECT MAX(week_index) FROM assignments)
        ),
        previous AS (
            SELECT student_id, AVG(avg_accuracy) AS previous_accuracy
            FROM weekly
            WHERE week_index < (SELECT MAX(week_index) FROM assignments)
            GROUP BY student_id
        ),
        weak_kp AS (
            SELECT q.student_id, kp.name AS weak_knowledge_point,
                   ROW_NUMBER() OVER (PARTITION BY q.student_id ORDER BY AVG(q.is_correct) ASC) AS rn
            FROM question_records q
            JOIN students s ON s.id = q.student_id
            JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
            WHERE {scope_condition}
            GROUP BY q.student_id, kp.name
        )
        SELECT st.id AS student_id, st.name AS student_name, c.grade || c.name AS class_name,
               ROUND(COALESCE(latest.avg_accuracy, 0) * 100, 1) AS latest_accuracy,
               ROUND(COALESCE(latest.submission_rate, 0) * 100, 1) AS submission_rate,
               ROUND((COALESCE(latest.avg_accuracy, 0) - COALESCE(previous.previous_accuracy, 0)) * 100, 1) AS delta_accuracy,
               weak_kp.weak_knowledge_point,
               ROUND((0.45 * (1 - COALESCE(latest.avg_accuracy, 0)) + 0.30 * (1 - COALESCE(latest.submission_rate, 0)) + 0.25 * MAX(0, COALESCE(previous.previous_accuracy, 0) - COALESCE(latest.avg_accuracy, 0))) * 100, 1) AS risk_score
        FROM students st
        JOIN classes c ON c.id = st.class_id
        LEFT JOIN latest ON latest.student_id = st.id
        LEFT JOIN previous ON previous.student_id = st.id
        LEFT JOIN weak_kp ON weak_kp.student_id = st.id AND weak_kp.rn = 1
        WHERE {student_condition}
        ORDER BY risk_score DESC, submission_rate ASC
        LIMIT 15
        """
        return Plan(intent, "template", "系统已识别出教师想筛出需要重点辅导的学生。", "综合正确率、提交率和退步幅度，生成高风险学生名单。", sql, "bar", f"{scope_name}高风险学生", "student_name", "risk_score", [])

    if intent == "weekly_report":
        sql = f"""
        SELECT kp.name AS knowledge_point,
               ROUND(AVG(q.is_correct) * 100, 1) AS accuracy_rate,
               ROUND((1 - AVG(q.is_correct)) * 100, 1) AS error_rate,
               COUNT(DISTINCT q.student_id) AS students_affected
        FROM question_records q
        JOIN assignments a ON a.id = q.assignment_id
        JOIN students s ON s.id = q.student_id
        JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
        WHERE {scope_condition} AND a.week_index >= (SELECT MAX(week_index) - 1 FROM assignments)
        GROUP BY kp.id, kp.name
        ORDER BY error_rate DESC
        LIMIT 8
        """
        return Plan(intent, "template", "系统已识别出教师需要生成本周学情报告。", "基于最近两周知识点表现，提炼本周学情亮点、问题与下周关注点。", sql, "bar", f"{scope_name}近两周知识点表现", "knowledge_point", "error_rate", [])

    if intent == "submission_rate":
        if class_id is not None:
            sql = f"""
            SELECT a.week_index,
                   ROUND(100.0 * AVG(CASE WHEN sub.status = 'submitted' THEN 1.0 ELSE 0.0 END), 1) AS submission_rate
            FROM submissions sub
            JOIN assignments a ON a.id = sub.assignment_id
            JOIN students s ON s.id = sub.student_id
            WHERE {scope_condition}
            GROUP BY a.week_index
            ORDER BY a.week_index
            LIMIT 8
            """
            return Plan(intent, "template", "系统已识别出教师在查看某个班级最近作业提交情况。", "按周统计作业提交率，判断该班是否出现投入下滑。", sql, "line", f"{scope_name}提交率趋势", "week_index", "submission_rate", [])
        sql = """
        SELECT a.week_index, c.grade || c.name AS class_name,
               ROUND(100.0 * AVG(CASE WHEN sub.status = 'submitted' THEN 1.0 ELSE 0.0 END), 1) AS submission_rate
        FROM submissions sub
        JOIN assignments a ON a.id = sub.assignment_id
        JOIN students s ON s.id = sub.student_id
        JOIN classes c ON c.id = s.class_id
        GROUP BY a.week_index, c.id, c.grade, c.name
        ORDER BY a.week_index, c.id
        LIMIT 48
        """
        series = [str(item["full_name"]) for item in list_classes()]
        return Plan(intent, "template", "系统已识别出教师想横向比较各班作业提交率。", "按周统计各班提交率，定位近阶段提交异常的班级。", sql, "line", "各班提交率趋势", "week_index", "submission_rate", series)

    if intent == "knowledge_point_students":
        if knowledge_point == "函数与方程":
            kp_filter = "kp.name IN ('一次函数', '二次函数', '方程求解')"
            title = "函数与方程"
        else:
            selected = _escape_sql(knowledge_point or "二次函数")
            kp_filter = f"kp.name = '{selected}'"
            title = knowledge_point or "二次函数"
        sql = f"""
        SELECT st.id AS student_id, st.name AS student_name, c.grade || c.name AS class_name,
               ROUND(AVG(q.is_correct) * 100, 1) AS accuracy_rate,
               COUNT(*) AS question_count
        FROM question_records q
        JOIN students st ON st.id = q.student_id
        JOIN classes c ON c.id = st.class_id
        JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
        WHERE {student_condition} AND {kp_filter}
        GROUP BY st.id, st.name, c.grade, c.name
        HAVING COUNT(*) >= 4
        ORDER BY accuracy_rate ASC
        LIMIT 15
        """
        return Plan(intent, "template", f"系统已识别出教师在关注 {title} 相关的薄弱学生。", "统计目标知识点上的学生正确率，筛出需要优先讲解和练习的对象。", sql, "bar", f"{title}薄弱学生", "student_name", "accuracy_rate", [])

    if intent == "high_effort_low_accuracy":
        sql = f"""
        WITH session_stats AS (
            SELECT ls.student_id, AVG(ls.duration_minutes) AS avg_duration
            FROM learning_sessions ls
            JOIN students s ON s.id = ls.student_id
            WHERE {scope_condition}
            GROUP BY ls.student_id
        ),
        accuracy_stats AS (
            SELECT sub.student_id, AVG(COALESCE(sub.correct_rate, 0)) * 100 AS accuracy_rate
            FROM submissions sub
            JOIN students s ON s.id = sub.student_id
            WHERE {scope_condition} AND sub.status = 'submitted'
            GROUP BY sub.student_id
        )
        SELECT st.id AS student_id, st.name AS student_name, c.grade || c.name AS class_name,
               ROUND(session_stats.avg_duration, 1) AS avg_duration,
               ROUND(accuracy_stats.accuracy_rate, 1) AS accuracy_rate
        FROM students st
        JOIN classes c ON c.id = st.class_id
        JOIN session_stats ON session_stats.student_id = st.id
        JOIN accuracy_stats ON accuracy_stats.student_id = st.id
        WHERE {student_condition} AND session_stats.avg_duration >= 80 AND accuracy_stats.accuracy_rate <= 62
        ORDER BY session_stats.avg_duration DESC, accuracy_stats.accuracy_rate ASC
        LIMIT 15
        """
        return Plan(intent, "template", "系统已识别出教师在关注学习投入高但效果不佳的学生。", "联动学习时长与正确率，找出可能存在学习方法问题的学生。", sql, "bar", "高投入低成效学生", "student_name", "avg_duration", [])

    if intent == "improving_students":
        sql = f"""
        WITH weekly AS (
            SELECT sub.student_id, a.week_index, AVG(COALESCE(sub.correct_rate, 0)) AS avg_accuracy
            FROM submissions sub
            JOIN assignments a ON a.id = sub.assignment_id
            JOIN students s ON s.id = sub.student_id
            WHERE {scope_condition}
            GROUP BY sub.student_id, a.week_index
        ),
        latest AS (
            SELECT student_id, avg_accuracy FROM weekly WHERE week_index = (SELECT MAX(week_index) FROM assignments)
        ),
        previous AS (
            SELECT student_id, AVG(avg_accuracy) AS previous_accuracy
            FROM weekly
            WHERE week_index < (SELECT MAX(week_index) FROM assignments)
            GROUP BY student_id
        )
        SELECT st.id AS student_id, st.name AS student_name, c.grade || c.name AS class_name,
               ROUND(COALESCE(latest.avg_accuracy, 0) * 100, 1) AS latest_accuracy,
               ROUND((COALESCE(latest.avg_accuracy, 0) - COALESCE(previous.previous_accuracy, 0)) * 100, 1) AS delta_accuracy
        FROM students st
        JOIN classes c ON c.id = st.class_id
        LEFT JOIN latest ON latest.student_id = st.id
        LEFT JOIN previous ON previous.student_id = st.id
        WHERE {student_condition}
        ORDER BY delta_accuracy DESC
        LIMIT 12
        """
        return Plan(intent, "template", "系统已识别出教师在寻找近期进步明显的学生。", "对比最近一周与前期平均表现，识别提升最快的学生。", sql, "bar", f"{scope_name}进步学生", "student_name", "delta_accuracy", [])

    if intent == "class_most_risk":
        sql = """
        WITH weekly AS (
            SELECT sub.student_id, a.week_index,
                   AVG(COALESCE(sub.correct_rate, 0)) AS avg_accuracy,
                   AVG(CASE WHEN sub.status = 'submitted' THEN 1.0 ELSE 0.0 END) AS submission_rate
            FROM submissions sub
            JOIN assignments a ON a.id = sub.assignment_id
            GROUP BY sub.student_id, a.week_index
        ),
        latest AS (
            SELECT student_id, avg_accuracy, submission_rate FROM weekly WHERE week_index = (SELECT MAX(week_index) FROM assignments)
        ),
        previous AS (
            SELECT student_id, AVG(avg_accuracy) AS previous_accuracy
            FROM weekly WHERE week_index < (SELECT MAX(week_index) FROM assignments)
            GROUP BY student_id
        ),
        student_risk AS (
            SELECT st.id AS student_id, st.class_id,
                   ROUND((0.45 * (1 - COALESCE(latest.avg_accuracy, 0)) + 0.30 * (1 - COALESCE(latest.submission_rate, 0)) + 0.25 * MAX(0, COALESCE(previous.previous_accuracy, 0) - COALESCE(latest.avg_accuracy, 0))) * 100, 1) AS risk_score
            FROM students st
            LEFT JOIN latest ON latest.student_id = st.id
            LEFT JOIN previous ON previous.student_id = st.id
        )
        SELECT c.grade || c.name AS class_name, COUNT(*) AS total_students,
               SUM(CASE WHEN student_risk.risk_score >= 42 THEN 1 ELSE 0 END) AS risk_students,
               ROUND(AVG(student_risk.risk_score), 1) AS avg_risk_score
        FROM student_risk
        JOIN classes c ON c.id = student_risk.class_id
        GROUP BY c.id, c.grade, c.name
        ORDER BY risk_students DESC, avg_risk_score DESC
        LIMIT 6
        """
        return Plan(intent, "template", "系统已识别出教师想比较各班风险学生分布。", "汇总各班风险学生数量与平均风险分数，定位风险压力最大的班级。", sql, "bar", "各班风险学生对比", "class_name", "risk_students", [])

    if intent == "knowledge_class_issue":
        target = _escape_sql(knowledge_point or "几何证明")
        sql = f"""
        SELECT c.grade || c.name AS class_name,
               ROUND(AVG(q.is_correct) * 100, 1) AS accuracy_rate,
               ROUND((1 - AVG(q.is_correct)) * 100, 1) AS error_rate,
               COUNT(*) AS record_count
        FROM question_records q
        JOIN students s ON s.id = q.student_id
        JOIN classes c ON c.id = s.class_id
        JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
        WHERE kp.name = '{target}'
        GROUP BY c.id, c.grade, c.name
        ORDER BY error_rate DESC
        LIMIT 6
        """
        return Plan(intent, "template", f"系统已识别出教师在比较 {knowledge_point or '几何证明'} 在不同班级中的问题程度。", "按班级统计目标知识点错误率，找出最需要优先干预的班级。", sql, "bar", f"{knowledge_point or '几何证明'}班级对比", "class_name", "error_rate", [])

    raise ValueError("unsupported_intent")

def _format_chart(plan: Plan, df: pd.DataFrame) -> ChartData:
    chart_rows = df.to_dict(orient="records")
    x_field = plan.x_field
    if plan.x_field == "week_index":
        for row in chart_rows:
            row["week_label"] = f"第{int(row['week_index'])}周"
        x_field = "week_label"
    return ChartData(type=plan.chart_type, title=plan.chart_title, x_field=x_field, y_field=plan.y_field, series=plan.series, data=chart_rows)


def _build_evidence(intent: str, df: pd.DataFrame, scope_label: str | None) -> list[EvidenceItem]:
    scope_text = scope_label or "全部班级"
    if df.empty:
        return [EvidenceItem(label="数据范围", value=scope_text, change="当前查询未返回有效结果")]

    top = df.iloc[0]
    evidence: list[EvidenceItem] = [EvidenceItem(label="数据范围", value=scope_text)]

    if intent == "declining_students":
        evidence.extend([
            EvidenceItem(label="退步最明显", value=str(top["student_name"]), change=f"{float(top['delta_accuracy']):.1f}%"),
            EvidenceItem(label="最近正确率", value=f"{float(top['latest_accuracy']):.1f}%"),
        ])
    elif intent == "weakest_knowledge":
        evidence.extend([
            EvidenceItem(label="最薄弱知识点", value=str(top["knowledge_point"]), change=f"错误率 {float(top['error_rate']):.1f}%"),
            EvidenceItem(label="样本记录", value=f"{int(top['record_count'])} 条"),
        ])
    elif intent == "at_risk_students":
        evidence.extend([
            EvidenceItem(label="风险学生数", value=f"{len(df)} 人"),
            EvidenceItem(label="最高风险分", value=f"{float(top['risk_score']):.1f}"),
        ])
    elif intent == "weekly_report":
        evidence.extend([
            EvidenceItem(label="首要薄弱点", value=str(top["knowledge_point"]), change=f"错误率 {float(top['error_rate']):.1f}%"),
            EvidenceItem(label="影响学生", value=f"{int(top['students_affected'])} 人"),
        ])
    elif intent == "submission_rate":
        if "class_name" in df.columns:
            worst = df.sort_values("submission_rate").iloc[0]
            evidence.extend([
                EvidenceItem(label="最低提交率", value=f"{float(worst['submission_rate']):.1f}%", change=str(worst["class_name"])),
                EvidenceItem(label="覆盖周次", value=f"{df['week_index'].nunique()} 周"),
            ])
        else:
            evidence.extend([
                EvidenceItem(label="最近提交率", value=f"{float(df.iloc[-1]['submission_rate']):.1f}%"),
                EvidenceItem(label="覆盖周次", value=f"{len(df)} 周"),
            ])
    elif intent == "knowledge_point_students":
        evidence.extend([
            EvidenceItem(label="最低正确率学生", value=str(top["student_name"]), change=f"{float(top['accuracy_rate']):.1f}%"),
            EvidenceItem(label="入选人数", value=f"{len(df)} 人"),
        ])
    elif intent == "high_effort_low_accuracy":
        evidence.extend([
            EvidenceItem(label="学习时长最高", value=f"{float(top['avg_duration']):.1f} 分钟"),
            EvidenceItem(label="代表学生", value=str(top["student_name"]), change=f"正确率 {float(top['accuracy_rate']):.1f}%"),
        ])
    elif intent == "improving_students":
        evidence.extend([
            EvidenceItem(label="进步最快", value=str(top["student_name"]), change=f"{float(top['delta_accuracy']):+.1f}%"),
            EvidenceItem(label="最近正确率", value=f"{float(top['latest_accuracy']):.1f}%"),
        ])
    elif intent == "class_most_risk":
        evidence.extend([
            EvidenceItem(label="风险班级", value=str(top["class_name"]), change=f"{int(top['risk_students'])} 人"),
            EvidenceItem(label="平均风险分", value=f"{float(top['avg_risk_score']):.1f}"),
        ])
    elif intent == "knowledge_class_issue":
        evidence.extend([
            EvidenceItem(label="问题最重班级", value=str(top["class_name"]), change=f"错误率 {float(top['error_rate']):.1f}%"),
            EvidenceItem(label="样本记录", value=f"{int(top['record_count'])} 条"),
        ])
    else:
        evidence.append(EvidenceItem(label="结果条数", value=f"{len(df)} 条"))

    return evidence[:3]


def _local_answer(plan: Plan, df: pd.DataFrame, scope_label: str | None) -> AgentAnswer:
    scope_text = scope_label or "全部班级"
    if df.empty:
        return AgentAnswer(
            problem_understanding=plan.understand,
            analysis_task=plan.task,
            headline="当前问题暂无足够数据支撑结论",
            summary="系统已完成数据检索，但当前数据范围内没有返回稳定结果。建议切换班级、缩小问题范围，或改为查询知识点、提交率、高风险学生等核心指标。",
            key_findings=["未检索到足够的有效记录。"],
            evidence=_build_evidence(plan.intent, df, scope_label),
            recommendations=["建议先查看班级整体周报或知识点表现，再继续追问。"],
            follow_up_questions=FOLLOW_UPS.get(plan.intent, FOLLOW_UPS["custom_sql"]),
        )

    top = df.iloc[0]

    if plan.intent == "declining_students":
        headline = f"{top['student_name']} 是当前退步最明显的学生"
        summary = f"在 {scope_text} 范围内，{top['student_name']} 最近一周正确率为 {float(top['latest_accuracy']):.1f}%，较前期平均下降 {abs(float(top['delta_accuracy'])):.1f} 个百分点，当前薄弱点集中在 {top['weak_knowledge_point']}。"
        findings = [f"共识别出 {len(df)} 名近期退步明显的学生。", f"下降幅度最大的学生是 {top['student_name']}，主要薄弱知识点为 {top['weak_knowledge_point']}。", "建议优先将下降幅度超过 8 个百分点的学生纳入本周跟踪名单。"]
        recommendations = ["对退步学生安排短时诊断练习，先确认是知识漏洞还是投入下降。", "围绕其薄弱知识点进行小组辅导，并在下周再次追踪正确率变化。", "结合提交记录和课堂参与情况，区分能力问题与学习习惯问题。"]
    elif plan.intent == "weakest_knowledge":
        headline = f"{top['knowledge_point']} 是当前最薄弱的知识点"
        summary = f"在 {scope_text} 范围内，{top['knowledge_point']} 的错误率达到 {float(top['error_rate']):.1f}%，是所有知识点中风险最高的环节，说明该主题需要优先安排讲解与巩固。"
        findings = [f"当前前 3 个薄弱知识点分别是：{'、'.join(df['knowledge_point'].head(3).tolist())}。", f"其中 {top['knowledge_point']} 的错误率最高，达到 {float(top['error_rate']):.1f}%。", "建议将高错误率知识点转化为下周课堂重点与随堂检测内容。"]
        recommendations = [f"优先围绕 {top['knowledge_point']} 做一次重难点回讲。", "安排 10 分钟针对性小测，快速确认错误来源。", "按学生错误类型进行分层讲评，避免一刀切复习。"]
    elif plan.intent == "at_risk_students":
        headline = f"已筛出 {len(df)} 名需要重点辅导的高风险学生"
        summary = f"系统综合最近正确率、作业提交率和退步幅度，识别出 {len(df)} 名高风险学生。名单前列学生同时存在正确率偏低、提交不稳定或近期退步的问题，适合优先纳入教师跟踪。"
        findings = [f"风险最高的学生是 {top['student_name']}，风险分为 {float(top['risk_score']):.1f}。", f"其最近正确率为 {float(top['latest_accuracy']):.1f}%，提交率为 {float(top['submission_rate']):.1f}%。", "高风险学生往往同时伴随知识点薄弱和学习投入下降。"]
        recommendations = ["先按风险分高低排序，建立本周重点辅导名单。", "对提交率低的学生增加提醒与反馈，对正确率低的学生增加知识点诊断。", "将高风险学生按知识点和行为特征分组，提升辅导效率。"]
    elif plan.intent == "weekly_report":
        weak_points = '、'.join(df['knowledge_point'].head(3).tolist())
        headline = f"{scope_text} 本周学情重点已生成"
        summary = f"最近两周数据显示，{scope_text} 当前最需要关注的知识点集中在 {weak_points}。其中 {top['knowledge_point']} 的错误率最高，为 {float(top['error_rate']):.1f}%，已影响 {int(top['students_affected'])} 名学生。"
        findings = [f"本周首要薄弱点是 {top['knowledge_point']}。", f"近两周问题较集中的 3 个知识点为 {weak_points}。", "建议将下周教学重点放在高错误率知识点的回讲和巩固上。"]
        recommendations = ["围绕前 3 个薄弱知识点安排一次分层复习。", "针对受影响学生较多的知识点设计短测，验证纠偏效果。", "将高风险学生与知识点复习计划结合，形成一周教学闭环。"]
    elif plan.intent == "submission_rate":
        if "class_name" in df.columns:
            lowest = df.sort_values('submission_rate').iloc[0]
            headline = f"{lowest['class_name']} 在最近提交率上最需要关注"
            summary = f"系统对比了各班最近 8 周作业提交情况。当前最低提交率记录出现在 {lowest['class_name']}，提交率为 {float(lowest['submission_rate']):.1f}%，说明该班在学习投入或作业跟进上存在明显波动。"
            findings = ["不同班级之间的提交率存在可观差异。", f"最低提交率对应 {lowest['class_name']}，为 {float(lowest['submission_rate']):.1f}%。", "建议对近两周下滑明显的班级优先做班级层面的提交干预。"]
            recommendations = ["对低提交率班级增加作业提醒与班级反馈。", "定位缺交集中学生，分析是否与作业难度或节奏有关。", "将提交率波动与课堂学习状态联动分析，避免只看结果不看过程。"]
        else:
            latest = float(df.iloc[-1]['submission_rate'])
            headline = f"{scope_text} 最近提交率为 {latest:.1f}%"
            summary = f"系统已读取 {scope_text} 最近 8 周作业提交记录。最新一周提交率为 {latest:.1f}%，可以用来判断该班近期作业完成稳定性是否出现波动。"
            findings = [f"最近一周提交率为 {latest:.1f}%。", f"当前共覆盖 {len(df)} 周历史记录。", "若最近两周曲线持续下滑，建议及时排查缺交原因。"]
            recommendations = ["优先查看最近两周缺交学生名单，进行点对点跟进。", "对连续缺交学生建立简短提醒机制。", "结合正确率一起判断，是投入不足还是任务难度过高。"]
    elif plan.intent == "knowledge_point_students":
        headline = f"{top['student_name']} 是当前该知识点最需关注的学生"
        summary = f"围绕目标知识点的答题记录统计显示，{top['student_name']} 当前正确率仅为 {float(top['accuracy_rate']):.1f}%。系统共筛出 {len(df)} 名该知识点表现偏弱的学生，可作为专项辅导对象。"
        findings = [f"本次共识别出 {len(df)} 名知识点薄弱学生。", f"正确率最低的学生是 {top['student_name']}，当前为 {float(top['accuracy_rate']):.1f}%。", "建议按相似错误类型分组辅导，提高一次讲解的覆盖效率。"]
        recommendations = ["先对薄弱学生做一次针对性例题讲解，再安排同类型练习。", "用 5 至 10 分钟随堂检测验证纠偏效果。", "对仍然偏弱的学生安排课后短任务，避免知识点再次堆积。"]
    elif plan.intent == "high_effort_low_accuracy":
        headline = f"已识别出 {len(df)} 名高投入低成效学生"
        summary = "系统发现这批学生学习时长较高，但作业正确率仍然偏低，说明问题更可能来自学习方法、错题复盘或知识建构方式，而不只是投入不足。"
        findings = [f"代表学生 {top['student_name']} 平均学习时长达到 {float(top['avg_duration']):.1f} 分钟，但正确率只有 {float(top['accuracy_rate']):.1f}%。", f"当前共识别出 {len(df)} 名类似特征学生。", "这类学生更适合做方法诊断，而不是单纯增加练习量。"]
        recommendations = ["优先检查错题复盘质量和解题步骤是否规范。", "安排示范性讲评，帮助学生建立更有效的学习路径。", "减少无效重复练习，转为高反馈的针对性练习。"]
    elif plan.intent == "improving_students":
        headline = f"{top['student_name']} 是最近进步最明显的学生"
        summary = f"在 {scope_text} 范围内，{top['student_name']} 最近一周正确率达到 {float(top['latest_accuracy']):.1f}%，较前期平均提升 {float(top['delta_accuracy']):.1f} 个百分点，说明其学习状态出现明显改善。"
        findings = [f"当前共识别出 {len(df)} 名近期进步明显的学生。", f"进步最快的学生为 {top['student_name']}，提升幅度为 {float(top['delta_accuracy']):.1f} 个百分点。", "建议将进步学生的学习策略沉淀为班级中的正向示范。"]
        recommendations = ["记录其近期学习变化，提炼可复制的做法。", "可在班级内进行同伴分享，形成正向示范。", "持续观察其是否能在后续周次保持稳定提升。"]
    elif plan.intent == "class_most_risk":
        headline = f"{top['class_name']} 当前风险学生最多"
        summary = f"系统对比各班风险学生数量后发现，{top['class_name']} 当前高风险学生数达到 {int(top['risk_students'])} 人，且平均风险分为 {float(top['avg_risk_score']):.1f}，说明该班需要优先进行班级层面的学情干预。"
        findings = [f"风险压力最大的班级是 {top['class_name']}。", f"该班高风险学生数量为 {int(top['risk_students'])} 人。", "建议先对该班的提交率、薄弱知识点和重点学生名单做联动排查。"]
        recommendations = ["将该班作为本周重点跟踪对象，先做班级层面的原因诊断。", "结合知识点薄弱项和提交率趋势，安排班级复习与提醒。", "对该班高风险学生建立更高频的个体反馈。"]
    elif plan.intent == "knowledge_class_issue":
        headline = f"{top['class_name']} 在该知识点上问题最严重"
        summary = f"系统比较了不同班级在目标知识点上的表现，发现 {top['class_name']} 的错误率最高，达到 {float(top['error_rate']):.1f}%。这说明该班在该主题上存在明显的集体性理解偏差。"
        findings = [f"问题最严重的班级是 {top['class_name']}。", f"其错误率为 {float(top['error_rate']):.1f}%，显著高于其他班级。", "建议优先从班级层面安排一次专题回讲和当堂检测。"]
        recommendations = ["针对该班组织一次知识点专题讲评。", "讲评后安排短测，验证是否真正完成纠偏。", "进一步下钻到学生名单，识别班级内最需要个别辅导的对象。"]
    else:
        headline = "已生成自定义学情分析结果"
        summary = plan.reason or "系统已根据教师问题检索学习数据并生成结果。"
        findings = [f"当前返回 {len(df)} 条结果。"]
        recommendations = ["建议结合图表和明细表继续追问，以获得更具体的教学动作。"]

    return AgentAnswer(problem_understanding=plan.understand, analysis_task=plan.task, headline=headline, summary=summary, key_findings=findings, evidence=_build_evidence(plan.intent, df, scope_label), recommendations=recommendations, follow_up_questions=FOLLOW_UPS.get(plan.intent, FOLLOW_UPS['custom_sql']))

def _refine_with_llm(question: str, plan: Plan, df: pd.DataFrame, answer: AgentAnswer, scope_label: str | None) -> AgentAnswer:
    settings = llm_settings()
    if not settings["available"]:
        return answer

    payload = {
        "question": question,
        "intent": plan.intent,
        "scope": scope_label or "全部班级",
        "headline": answer.headline,
        "summary": answer.summary,
        "key_findings": answer.key_findings,
        "evidence": [item.model_dump() for item in answer.evidence],
        "recommendations": answer.recommendations,
        "follow_up_questions": answer.follow_up_questions,
        "sample_rows": _rows(df.head(6)),
        "instruction": "请润色成教师可直接阅读的中文 JSON，保留 headline、summary、key_findings、recommendations、follow_up_questions 字段。",
    }
    refined = summarize_result(payload)
    if not refined:
        return answer

    return AgentAnswer(
        problem_understanding=answer.problem_understanding,
        analysis_task=answer.analysis_task,
        headline=str(refined.get("headline", answer.headline)),
        summary=str(refined.get("summary", answer.summary)),
        key_findings=[str(item) for item in refined.get("key_findings", answer.key_findings)][:4] or answer.key_findings,
        evidence=answer.evidence,
        recommendations=[str(item) for item in refined.get("recommendations", answer.recommendations)][:4] or answer.recommendations,
        follow_up_questions=[str(item) for item in refined.get("follow_up_questions", answer.follow_up_questions)][:4] or answer.follow_up_questions,
    )


def _custom_plan(question: str, scope_label: str | None) -> Plan | None:
    payload = generate_sql_plan(question, scope_label)
    if not payload:
        return None

    sql = str(payload.get("sql") or "").strip()
    if not sql:
        return Plan(
            intent="custom_sql",
            mode="fallback",
            understand="系统已理解教师的问题，但当前数据范围无法直接回答。",
            task=str(payload.get("reason") or "缺少必要数据或字段支持。"),
            sql="SELECT 1 AS placeholder WHERE 1 = 0",
            chart_type="table",
            chart_title="查询结果",
            x_field="placeholder",
            y_field=None,
            series=[],
            reason=str(payload.get("reason") or "当前数据无法回答该问题。"),
        )

    chart_type = str(payload.get("chart_type") or "table")
    if chart_type not in {"bar", "line", "table", "pie"}:
        chart_type = "table"
    return Plan(
        intent=str(payload.get("intent") or "custom_sql"),
        mode="llm",
        understand="系统已使用 DeepSeek 理解教师问题，并生成对应的数据分析计划。",
        task=str(payload.get("analysis_focus") or payload.get("reason") or "根据问题生成自定义查询并提炼分析重点。"),
        sql=sql,
        chart_type=chart_type,
        chart_title="自定义学情分析",
        x_field=str(payload.get("x_field") or "label"),
        y_field=str(payload.get("y_field")) if payload.get("y_field") is not None else None,
        series=[],
        reason=str(payload.get("reason") or ""),
    )


def _trace(plan: Plan, llm_used: bool) -> list[TraceStep]:
    return [
        TraceStep(step="理解教师问题", status="done", detail=plan.understand),
        TraceStep(step="识别分析任务", status="done", detail=plan.task),
        TraceStep(step="构建数据查询计划", status="done", detail="命中稳定模板链路。" if plan.mode == "template" else "已结合 DeepSeek 生成查询计划，并进行安全校验。"),
        TraceStep(step="读取学习记录", status="done", detail="已从 SQLite 中读取作业、答题与学习行为数据。"),
        TraceStep(step="计算关键指标", status="done", detail="已完成正确率、提交率、风险或知识点指标计算。"),
        TraceStep(step="生成教学建议", status="done", detail="已输出教师可直接使用的诊断结论与建议。" + (" 本次结果包含 DeepSeek 在线增强。" if llm_used else " 当前为离线模板结果。")),
    ]


def _fallback(question: str, reason: str, debug: DebugInfo | None = None) -> AgentResponse:
    answer = AgentAnswer(
        problem_understanding="系统已接收教师问题，但当前问题未能映射到稳定的数据分析口径。",
        analysis_task="建议改为查询班级报告、知识点薄弱项、提交率、高风险学生或指定班级的周度表现。",
        headline="当前问题暂时无法稳定回答",
        summary="系统已拒绝执行不安全或无法解释的请求。你可以尝试换一种更贴近教学数据的问题表达方式。",
        key_findings=[reason],
        evidence=[EvidenceItem(label="处理结果", value="未执行查询", change=reason)],
        recommendations=["建议改用班级、知识点、提交率、风险学生等结构化问法继续提问。"],
        follow_up_questions=["生成一份本周班级学情报告。", "帮我找出需要重点辅导的学生。"],
    )
    return AgentResponse(
        mode="fallback",
        intent="fallback",
        question=question,
        answer=answer,
        trace=[TraceStep(step="理解教师问题", status="done", detail="系统已收到教师问题。"), TraceStep(step="识别分析任务", status="warning", detail=reason), TraceStep(step="生成教学建议", status="done", detail="已返回更稳妥的追问建议。")],
        table=TableData(columns=[], rows=[]),
        chart=ChartData(type="table", title="暂无结果", x_field="none", y_field=None, data=[]),
        debug=debug or DebugInfo(),
    )


def run_agent(question: str, class_id: int | None = None, developer_mode: bool = False) -> AgentResponse:
    trimmed = question.strip()
    if not trimmed:
        return _fallback(question, "请输入一个具体的教学分析问题。")
    if _is_dangerous(trimmed):
        return _fallback(trimmed, "检测到危险请求，系统仅支持只读学情分析，不允许修改或删除数据。", DebugInfo(reason="dangerous_request_rejected"))

    effective_class_id, scope_label = _class_context(trimmed, class_id)
    intent = detect_template_intent(trimmed)
    settings = llm_settings()
    llm_used = False

    if intent:
        plan = _template_plan(intent, trimmed, effective_class_id, scope_label)
    else:
        plan = _custom_plan(trimmed, scope_label)
        if plan is None:
            closest = _closest_template_intent(trimmed)
            if closest:
                plan = _template_plan(closest, trimmed, effective_class_id, scope_label)
            else:
                return _fallback(trimmed, "当前数据无法回答该问题，请尝试换一种更明确的问法。")
        elif plan.mode == "fallback":
            return _fallback(trimmed, plan.reason or "当前数据无法回答该问题。")
        else:
            llm_used = True

    try:
        safe_sql = validate_select_sql(plan.sql)
    except ValueError as exc:
        if plan.mode == "llm":
            closest = _closest_template_intent(trimmed)
            if closest:
                plan = _template_plan(closest, trimmed, effective_class_id, scope_label)
                safe_sql = validate_select_sql(plan.sql)
                llm_used = False
            else:
                return _fallback(trimmed, f"大模型生成的查询未通过安全校验：{exc}", DebugInfo(sql=plan.sql if developer_mode else None, llm_used=True, model=settings['model'], reason=str(exc)))
        else:
            raise

    try:
        df = _run(safe_sql)
    except Exception as exc:
        if plan.mode == "llm":
            closest = _closest_template_intent(trimmed)
            if closest:
                plan = _template_plan(closest, trimmed, effective_class_id, scope_label)
                safe_sql = validate_select_sql(plan.sql)
                df = _run(safe_sql)
                llm_used = False
            else:
                return _fallback(trimmed, f"查询执行失败：{exc}", DebugInfo(sql=safe_sql if developer_mode else None, llm_used=True, model=settings['model'], reason=str(exc)))
        else:
            raise

    answer = _local_answer(plan, df, scope_label)
    refined_answer = _refine_with_llm(trimmed, plan, df, answer, scope_label)
    if settings["available"] and refined_answer != answer:
        llm_used = True

    return AgentResponse(
        mode=plan.mode if plan.mode in {"template", "llm"} else "fallback",
        intent=plan.intent,
        question=trimmed,
        answer=refined_answer,
        trace=_trace(plan, llm_used),
        table=TableData(columns=list(df.columns), rows=_rows(df)),
        chart=_format_chart(plan, df),
        debug=DebugInfo(sql=safe_sql if developer_mode else None, llm_used=llm_used, model=settings["model"] if llm_used else None, reason=plan.reason or None),
    )


def validate_sql(sql: str) -> str:
    return validate_select_sql(sql)
