from __future__ import annotations

from typing import Any

import pandas as pd

from .db import get_connection
from .schemas import DashboardMeta, DashboardResponse, KpiCard, StudentProfileResponse


ACCURACY_KEY = "平均正确率"
SUBMISSION_KEY = "提交率"
KNOWLEDGE_KEY = "知识点正确率"


def _read_frame(sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def _max_week() -> int:
    df = _read_frame("SELECT MAX(week_index) AS max_week FROM assignments")
    return int(df.iloc[0]["max_week"]) if not df.empty and df.iloc[0]["max_week"] else 8


def _week_window(weeks: int) -> tuple[int, int]:
    max_week = _max_week()
    valid_weeks = max(4, min(weeks, max_week))
    min_week = max(1, max_week - valid_weeks + 1)
    return min_week, max_week


def list_classes() -> list[dict[str, Any]]:
    df = _read_frame(
        """
        SELECT
            c.id,
            c.name,
            c.grade,
            c.teacher_name,
            c.grade || c.name AS full_name,
            COUNT(s.id) AS student_count
        FROM classes c
        LEFT JOIN students s ON s.class_id = c.id
        GROUP BY c.id, c.name, c.grade, c.teacher_name
        ORDER BY c.id
        """
    )
    return df.to_dict(orient="records")


def list_students(class_id: int | None = None) -> list[dict[str, Any]]:
    sql = """
    SELECT
        s.id,
        s.name,
        s.class_id,
        c.grade || c.name AS class_name,
        c.teacher_name
    FROM students s
    JOIN classes c ON c.id = s.class_id
    """
    params: tuple[Any, ...] = ()
    if class_id is not None:
        sql += " WHERE s.class_id = ?"
        params = (class_id,)
    sql += " ORDER BY s.class_id, s.id"
    return _read_frame(sql, params).to_dict(orient="records")


def _class_scope_sql(class_id: int | None, alias: str = "s") -> tuple[str, tuple[Any, ...]]:
    if class_id is None:
        return "1 = 1", ()
    return f"{alias}.class_id = ?", (class_id,)


def _risk_frame(class_id: int | None = None, weeks: int = 8) -> pd.DataFrame:
    min_week, max_week = _week_window(weeks)
    condition, params = _class_scope_sql(class_id)
    latest_condition = condition.replace("s.", "s1.")
    previous_condition = condition.replace("s.", "s2.")
    weak_condition = condition.replace("s.", "s3.")
    session_condition = condition.replace("s.", "s4.")
    student_condition = condition.replace("s.", "st.")

    sql = f"""
    WITH latest AS (
        SELECT
            sub.student_id,
            AVG(COALESCE(sub.correct_rate, 0)) AS latest_accuracy,
            AVG(CASE WHEN sub.status = 'submitted' THEN 1.0 ELSE 0.0 END) AS latest_submission
        FROM submissions sub
        JOIN assignments a ON a.id = sub.assignment_id
        JOIN students s1 ON s1.id = sub.student_id
        WHERE {latest_condition} AND a.week_index = ?
        GROUP BY sub.student_id
    ),
    previous AS (
        SELECT
            sub.student_id,
            AVG(COALESCE(sub.correct_rate, 0)) AS previous_accuracy
        FROM submissions sub
        JOIN assignments a ON a.id = sub.assignment_id
        JOIN students s2 ON s2.id = sub.student_id
        WHERE {previous_condition} AND a.week_index BETWEEN ? AND ?
        GROUP BY sub.student_id
    ),
    weak_kp AS (
        SELECT
            q.student_id,
            kp.name AS weak_knowledge_point,
            ROW_NUMBER() OVER (PARTITION BY q.student_id ORDER BY AVG(q.is_correct) ASC) AS rn
        FROM question_records q
        JOIN assignments a ON a.id = q.assignment_id
        JOIN students s3 ON s3.id = q.student_id
        JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
        WHERE {weak_condition} AND a.week_index BETWEEN ? AND ?
        GROUP BY q.student_id, kp.name
    ),
    session_stats AS (
        SELECT
            ls.student_id,
            AVG(ls.duration_minutes) AS avg_duration
        FROM learning_sessions ls
        JOIN students s4 ON s4.id = ls.student_id
        WHERE {session_condition} AND ls.week_index BETWEEN ? AND ?
        GROUP BY ls.student_id
    )
    SELECT
        st.id AS student_id,
        st.name AS student_name,
        c.grade || c.name AS class_name,
        ROUND(COALESCE(latest.latest_accuracy, 0) * 100, 1) AS latest_accuracy,
        ROUND(COALESCE(latest.latest_submission, 0) * 100, 1) AS submission_rate,
        ROUND((COALESCE(latest.latest_accuracy, 0) - COALESCE(previous.previous_accuracy, 0)) * 100, 1) AS delta_accuracy,
        ROUND(COALESCE(session_stats.avg_duration, 0), 1) AS avg_duration,
        weak_kp.weak_knowledge_point,
        ROUND(
            (
                0.45 * (1 - COALESCE(latest.latest_accuracy, 0)) +
                0.30 * (1 - COALESCE(latest.latest_submission, 0)) +
                0.25 * MAX(0, COALESCE(previous.previous_accuracy, 0) - COALESCE(latest.latest_accuracy, 0))
            ) * 100,
            1
        ) AS risk_score
    FROM students st
    JOIN classes c ON c.id = st.class_id
    LEFT JOIN latest ON latest.student_id = st.id
    LEFT JOIN previous ON previous.student_id = st.id
    LEFT JOIN weak_kp ON weak_kp.student_id = st.id AND weak_kp.rn = 1
    LEFT JOIN session_stats ON session_stats.student_id = st.id
    WHERE {student_condition}
    ORDER BY risk_score DESC, delta_accuracy ASC, submission_rate ASC
    """
    query_params = (
        params
        + (max_week,)
        + params
        + (min_week, max(max_week - 1, min_week))
        + params
        + (min_week, max_week)
        + params
        + (min_week, max_week)
        + params
    )
    return _read_frame(sql, query_params)


def get_dashboard_data(class_id: int | None = None, weeks: int = 8) -> DashboardResponse:
    min_week, max_week = _week_window(weeks)
    class_condition, params = _class_scope_sql(class_id)

    student_df = _read_frame(f"SELECT COUNT(*) AS total_students FROM students s WHERE {class_condition}", params)
    total_students = int(student_df.iloc[0]["total_students"]) if not student_df.empty else 0

    if class_id is None:
        scope_label = "全部班级"
    else:
        scope_df = _read_frame("SELECT grade || name AS scope_label FROM classes WHERE id = ?", (class_id,))
        scope_label = str(scope_df.iloc[0]["scope_label"]) if not scope_df.empty else f"班级 {class_id}"

    accuracy_df = _read_frame(
        f"""
        SELECT
            a.week_index,
            ROUND(AVG(sub.correct_rate) * 100, 1) AS avg_accuracy
        FROM submissions sub
        JOIN assignments a ON a.id = sub.assignment_id
        JOIN students s ON s.id = sub.student_id
        WHERE {class_condition} AND a.week_index BETWEEN ? AND ? AND sub.status = 'submitted'
        GROUP BY a.week_index
        ORDER BY a.week_index
        """,
        params + (min_week, max_week),
    )

    submission_df = _read_frame(
        f"""
        SELECT
            a.week_index,
            ROUND(100.0 * AVG(CASE WHEN sub.status = 'submitted' THEN 1.0 ELSE 0.0 END), 1) AS submission_rate
        FROM submissions sub
        JOIN assignments a ON a.id = sub.assignment_id
        JOIN students s ON s.id = sub.student_id
        WHERE {class_condition} AND a.week_index BETWEEN ? AND ?
        GROUP BY a.week_index
        ORDER BY a.week_index
        """,
        params + (min_week, max_week),
    )

    knowledge_df = _read_frame(
        f"""
        SELECT
            kp.name AS knowledge_point,
            ROUND(AVG(q.is_correct) * 100, 1) AS accuracy
        FROM question_records q
        JOIN assignments a ON a.id = q.assignment_id
        JOIN students s ON s.id = q.student_id
        JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
        WHERE {class_condition} AND a.week_index BETWEEN ? AND ?
        GROUP BY kp.id, kp.name
        ORDER BY accuracy ASC
        """,
        params + (min_week, max_week),
    )

    risk_all_df = _risk_frame(class_id=class_id, weeks=weeks)
    risk_top_df = risk_all_df.head(8).copy()

    latest_accuracy = float(accuracy_df.iloc[-1]["avg_accuracy"]) if not accuracy_df.empty else 0.0
    previous_accuracy = float(accuracy_df.iloc[-2]["avg_accuracy"]) if len(accuracy_df) > 1 else latest_accuracy
    latest_submission = float(submission_df.iloc[-1]["submission_rate"]) if not submission_df.empty else 0.0
    previous_submission = float(submission_df.iloc[-2]["submission_rate"]) if len(submission_df) > 1 else latest_submission
    risk_count = int((risk_all_df["risk_score"] >= 42).sum()) if not risk_all_df.empty else 0
    declining_count = int((risk_all_df["delta_accuracy"] <= -8).sum()) if not risk_all_df.empty else 0
    weak_knowledge_count = int((knowledge_df["accuracy"] < 70).sum()) if not knowledge_df.empty else 0

    kpis = [
        KpiCard(
            label="平均正确率",
            value=f"{latest_accuracy:.1f}%",
            delta=f"{latest_accuracy - previous_accuracy:+.1f} pct",
            trend="up" if latest_accuracy > previous_accuracy else "down" if latest_accuracy < previous_accuracy else "flat",
        ),
        KpiCard(
            label="作业提交率",
            value=f"{latest_submission:.1f}%",
            delta=f"{latest_submission - previous_submission:+.1f} pct",
            trend="up" if latest_submission > previous_submission else "down" if latest_submission < previous_submission else "flat",
        ),
        KpiCard(label="高风险学生", value=f"{risk_count} 人", delta="重点关注", trend="down" if risk_count else "flat"),
        KpiCard(label="退步学生", value=f"{declining_count} 人", delta="较上周下降", trend="down" if declining_count else "flat"),
        KpiCard(label="薄弱知识点数", value=f"{weak_knowledge_count} 个", delta="低于 70%", trend="down" if weak_knowledge_count else "flat"),
    ]

    risk_students: list[dict[str, Any]] = []
    for row in risk_top_df.to_dict(orient="records"):
        avg_duration = float(row["avg_duration"])
        latest_accuracy_value = float(row["latest_accuracy"])
        submission_rate_value = float(row["submission_rate"])
        if avg_duration >= 85 and latest_accuracy_value <= 62:
            action = "建议先排查学习方法与错题复盘质量，再安排针对性讲解。"
        elif submission_rate_value <= 78 and latest_accuracy_value >= 68:
            action = "建议优先提升作业投入度，安排固定提交提醒和跟进。"
        else:
            action = "建议纳入本周重点辅导名单，并跟踪知识点巩固情况。"
        risk_students.append(
            {
                "student_id": int(row["student_id"]),
                "student_name": row["student_name"],
                "class_name": row["class_name"],
                "latest_accuracy": latest_accuracy_value,
                "delta_accuracy": float(row["delta_accuracy"]),
                "submission_rate": submission_rate_value,
                "weak_knowledge_point": row["weak_knowledge_point"],
                "risk_score": float(row["risk_score"]),
                "action": action,
            }
        )

    return DashboardResponse(
        meta=DashboardMeta(scope_label=scope_label, student_count=total_students, weeks=max_week - min_week + 1),
        kpis=kpis,
        accuracy_trend=[
            {"week": f"第{int(item['week_index'])}周", ACCURACY_KEY: float(item["avg_accuracy"])}
            for item in accuracy_df.to_dict(orient="records")
        ],
        submission_trend=[
            {"week": f"第{int(item['week_index'])}周", SUBMISSION_KEY: float(item["submission_rate"])}
            for item in submission_df.to_dict(orient="records")
        ],
        knowledge_mastery=[
            {"knowledge_point": item["knowledge_point"], KNOWLEDGE_KEY: float(item["accuracy"])}
            for item in knowledge_df.to_dict(orient="records")
        ],
        risk_students=risk_students,
    )


def get_student_profile(student_id: int) -> StudentProfileResponse:
    profile_df = _read_frame(
        """
        SELECT
            s.id,
            s.name,
            s.gender,
            s.class_id,
            c.grade || c.name AS class_name,
            c.teacher_name
        FROM students s
        JOIN classes c ON c.id = s.class_id
        WHERE s.id = ?
        """,
        (student_id,),
    )
    if profile_df.empty:
        raise ValueError("student_not_found")

    weekly_df = _read_frame(
        """
        SELECT
            a.week_index,
            ROUND(AVG(COALESCE(sub.correct_rate, 0)) * 100, 1) AS avg_accuracy,
            ROUND(100.0 * AVG(CASE WHEN sub.status = 'submitted' THEN 1.0 ELSE 0.0 END), 1) AS submission_rate
        FROM submissions sub
        JOIN assignments a ON a.id = sub.assignment_id
        WHERE sub.student_id = ?
        GROUP BY a.week_index
        ORDER BY a.week_index
        """,
        (student_id,),
    )

    weak_df = _read_frame(
        """
        SELECT
            kp.name AS knowledge_point,
            ROUND(AVG(q.is_correct) * 100, 1) AS accuracy
        FROM question_records q
        JOIN knowledge_points kp ON kp.id = q.knowledge_point_id
        WHERE q.student_id = ?
        GROUP BY kp.id, kp.name
        ORDER BY accuracy ASC
        LIMIT 5
        """,
        (student_id,),
    )

    submission_df = _read_frame(
        """
        SELECT
            a.title,
            a.week_index,
            kp.name AS knowledge_point,
            sub.status,
            ROUND(COALESCE(sub.correct_rate, 0) * 100, 1) AS correct_rate,
            ROUND(COALESCE(sub.time_spent_minutes, 0), 1) AS time_spent_minutes
        FROM submissions sub
        JOIN assignments a ON a.id = sub.assignment_id
        JOIN knowledge_points kp ON kp.id = a.knowledge_point_id
        WHERE sub.student_id = ?
        ORDER BY a.week_index DESC, a.id DESC
        LIMIT 8
        """,
        (student_id,),
    )

    latest_accuracy = float(weekly_df.iloc[-1]["avg_accuracy"]) if not weekly_df.empty else 0.0
    previous_accuracy = float(weekly_df.iloc[:-1]["avg_accuracy"].mean()) if len(weekly_df) > 1 else latest_accuracy
    latest_submission = float(weekly_df.iloc[-1]["submission_rate"]) if not weekly_df.empty else 0.0
    delta_accuracy = latest_accuracy - previous_accuracy
    weak_points = "、".join(weak_df["knowledge_point"].head(2).tolist()) if not weak_df.empty else "暂无明显薄弱项"

    risk_tags: list[str] = []
    if latest_accuracy < 62:
        risk_tags.append("正确率偏低")
    if latest_submission < 80:
        risk_tags.append("提交率偏低")
    if delta_accuracy <= -8:
        risk_tags.append("近期退步")
    if not risk_tags:
        risk_tags.append("整体稳定")

    if delta_accuracy <= -8:
        change_text = "最近两周出现明显退步"
    elif delta_accuracy >= 8:
        change_text = "最近两周进步较快"
    else:
        change_text = "最近表现整体平稳"

    insight = (
        f"{profile_df.iloc[0]['name']} 当前最近一周平均正确率为 {latest_accuracy:.1f}%，作业提交率为 {latest_submission:.1f}%。"
        f"{change_text}，当前需要优先关注 {weak_points}。"
    )

    recommendations = [
        f"围绕 {weak_points} 安排 1 次短时讲解和 1 次针对练习。",
        "结合最近 2 周作业与课堂表现进行一次个别反馈，明确下周目标。",
        "持续跟踪提交节奏与错题复盘情况，避免问题重复出现。",
    ]

    profile = profile_df.iloc[0].to_dict()
    profile.update(
        {
            "latest_accuracy": round(latest_accuracy, 1),
            "latest_submission_rate": round(latest_submission, 1),
            "recent_change": round(delta_accuracy, 1),
            "risk_tags": risk_tags,
        }
    )

    return StudentProfileResponse(
        profile=profile,
        weekly_accuracy=[
            {
                "week": f"第{int(item['week_index'])}周",
                ACCURACY_KEY: float(item["avg_accuracy"]),
                SUBMISSION_KEY: float(item["submission_rate"]),
            }
            for item in weekly_df.to_dict(orient="records")
        ],
        submission_summary=submission_df.to_dict(orient="records"),
        weak_knowledge_points=weak_df.to_dict(orient="records"),
        insight=insight,
        recommendations=recommendations,
    )
