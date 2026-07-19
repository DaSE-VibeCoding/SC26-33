from __future__ import annotations


SCHEMA_OVERVIEW = """
你可以查询一个教师侧学习分析 SQLite 数据库。
可用表：
1. classes(id, name, grade, teacher_name)
2. students(id, name, class_id, gender, enrollment_status)
3. knowledge_points(id, name, subject)
4. assignments(id, title, class_id, knowledge_point_id, assigned_date, due_date, week_index, max_score)
5. submissions(id, assignment_id, student_id, submitted_at, status, score, correct_rate, time_spent_minutes)
6. question_records(id, assignment_id, student_id, knowledge_point_id, question_no, is_correct, score, answered_at)
7. learning_sessions(id, student_id, session_date, week_index, duration_minutes, activity_type, engagement_score, knowledge_point_id)
8. interventions(id, student_id, class_id, created_at, risk_level, focus_area, action_suggestion, status)

字段说明：
- correct_rate 是 0 到 1 的小数，前端展示时再乘 100。
- status 主要取值 submitted / missing。
- week_index 表示最近 8 周中的周次，8 是最新周。
- question_records.is_correct 取值 0 或 1，可用于统计知识点正确率。
- classes.grade || classes.name 可以拼成完整班级名，例如 七年级3班。
"""

ANALYSIS_RULES = """
常用分析口径：
- 退步学生：比较最新周与前期平均正确率差值。
- 高风险学生：综合正确率、提交率、退步幅度。
- 薄弱知识点：按 question_records 的平均正确率排序。
- 提交率：按 submitted 占比计算。
- 学习时长高但正确率低：联合 learning_sessions.duration_minutes 与 submissions.correct_rate 判断。
"""

SQL_CONSTRAINTS = """
SQL 约束：
- 只允许输出单条 SQLite SELECT 或 WITH 查询。
- 禁止 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE、REPLACE、TRUNCATE、ATTACH、DETACH、PRAGMA、VACUUM。
- 不要编造不存在的表和字段。
- 默认查询结果 LIMIT 20；聚合排行榜 LIMIT 10。
- 如果数据无法回答问题，返回空 sql 并写明原因。
- 输出必须是 JSON，不要使用 Markdown 代码块。
"""

EXAMPLE_SQL = [
    {
        "question": "哪个知识点错误率最高？",
        "sql": """
        SELECT
            kp.name AS knowledge_point,
            ROUND(AVG(q.is_correct) * 100, 1) AS accuracy_rate,
            ROUND((1 - AVG(q.is_correct)) * 100, 1) AS error_rate
        FROM question_records q
        JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
        GROUP BY kp.id, kp.name
        ORDER BY error_rate DESC
        LIMIT 10
        """.strip(),
    },
    {
        "question": "七年级3班最近作业提交率怎么样？",
        "sql": """
        SELECT
            a.week_index,
            ROUND(100.0 * AVG(CASE WHEN sub.status = 'submitted' THEN 1.0 ELSE 0.0 END), 1) AS submission_rate
        FROM submissions sub
        JOIN assignments a ON a.id = sub.assignment_id
        JOIN students s ON s.id = sub.student_id
        WHERE s.class_id = 3
        GROUP BY a.week_index
        ORDER BY a.week_index
        LIMIT 8
        """.strip(),
    },
]

SUMMARY_SYSTEM_PROMPT = (
    "你是一名教师侧学习分析助手。请根据给定数据证据，输出教师可直接理解的中文结论、关键发现和教学建议。只输出 JSON。"
)


def build_sql_messages(question: str, class_context: str | None = None) -> list[dict[str, str]]:
    class_line = f"当前班级上下文：{class_context}\n" if class_context else ""
    examples = "\n\n".join(f"问题：{item['question']}\nSQL：{item['sql']}" for item in EXAMPLE_SQL)
    user_prompt = (
        f"{class_line}"
        f"{SCHEMA_OVERVIEW}\n"
        f"{ANALYSIS_RULES}\n"
        f"{SQL_CONSTRAINTS}\n"
        f"示例：\n{examples}\n\n"
        "请根据教师问题生成 JSON：\n"
        '{'
        '"intent":"custom_sql",'
        '"reason":"...",'
        '"sql":"SELECT ...",'
        '"chart_type":"bar|line|table|pie",'
        '"x_field":"...",'
        '"y_field":"...",'
        '"analysis_focus":"..."'
        '}\n\n'
        f"教师问题：{question}"
    )
    return [
        {"role": "system", "content": "你是 SQLite Text-to-SQL 规划器，只输出 JSON。"},
        {"role": "user", "content": user_prompt},
    ]


def build_summary_messages(payload: dict[str, object]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": str(payload)},
    ]
