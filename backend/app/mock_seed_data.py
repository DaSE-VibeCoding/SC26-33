from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np


SEED = 20250630
WEEKS = 8
ASSIGNMENT_WEEKS = [1, 1, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8]
QUESTION_COUNT_PER_ASSIGNMENT = 6
SESSION_TYPES = ["课堂练习", "课后巩固", "错题复盘", "自主学习"]

KNOWLEDGE_POINTS = [
    ("一次函数", "数学"),
    ("二次函数", "数学"),
    ("方程求解", "数学"),
    ("几何证明", "数学"),
    ("概率统计", "数学"),
    ("数据分析", "数学"),
    ("阅读理解", "语文"),
    ("写作表达", "语文"),
    ("词汇积累", "英语"),
    ("实验探究", "科学"),
    ("信息检索", "信息技术"),
    ("逻辑推理", "综合"),
]

CLASS_CONFIG = [
    {"id": 1, "name": "1班", "grade": "七年级", "teacher_name": "林老师"},
    {"id": 2, "name": "2班", "grade": "七年级", "teacher_name": "周老师"},
    {"id": 3, "name": "3班", "grade": "七年级", "teacher_name": "陈老师"},
    {"id": 4, "name": "4班", "grade": "七年级", "teacher_name": "蒋老师"},
    {"id": 5, "name": "5班", "grade": "七年级", "teacher_name": "沈老师"},
    {"id": 6, "name": "6班", "grade": "七年级", "teacher_name": "韩老师"},
]

CLASS_SIZES = [39, 41, 40, 38, 42, 39]
CLASS_ACCURACY_ADJUST = {1: 0.05, 2: -0.02, 3: -0.04, 4: 0.01, 5: -0.01, 6: 0.03}
CLASS_SUBMISSION_ADJUST = {1: 0.03, 2: 0.01, 3: -0.03, 4: 0.0, 5: -0.01, 6: 0.02}
CLASS_ENGAGEMENT_ADJUST = {1: 0.02, 2: 0.0, 3: -0.02, 4: 0.01, 5: -0.01, 6: 0.02}

KNOWLEDGE_ACCURACY_ADJUST = {
    1: 0.01,
    2: -0.12,
    3: -0.04,
    4: -0.06,
    5: -0.02,
    6: 0.0,
    7: 0.02,
    8: 0.01,
    9: 0.01,
    10: -0.01,
    11: 0.0,
    12: -0.03,
}

SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹")
GIVEN_NAMES = [
    "子涵", "雨桐", "欣怡", "宇轩", "梓萌", "浩然", "诗涵", "嘉怡", "俊杰", "思源",
    "晨曦", "若曦", "一诺", "锦程", "可欣", "明轩", "睿哲", "佳宁", "泽宇", "梦琪",
    "亦凡", "天佑", "沐阳", "芷晴", "皓轩", "安琪", "泽楷", "馨月", "博文", "佳怡",
    "子墨", "希妍", "承泽", "雨菲", "嘉豪", "思远", "沐宸", "若彤", "昊天", "语汐",
    "启航", "知远", "书言", "嘉宁", "景行", "乐妍", "言蹊", "奕辰",
]


def _student_names(total: int) -> list[str]:
    names: list[str] = []
    idx = 0
    while len(names) < total:
        surname = SURNAMES[idx % len(SURNAMES)]
        given = GIVEN_NAMES[(idx * 7) % len(GIVEN_NAMES)]
        name = f"{surname}{given}"
        if name not in names:
            names.append(name)
        idx += 1
    return names


def _week_start(today: date, week_index: int) -> date:
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(weeks=(WEEKS - week_index))


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate_database(db_path: Path) -> None:
    rng = np.random.default_rng(SEED)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    total_students = sum(CLASS_SIZES)
    student_names = _student_names(total_students)

    decline_students = set(rng.choice(np.arange(1, total_students + 1), size=16, replace=False).tolist())
    remaining = np.array([sid for sid in range(1, total_students + 1) if sid not in decline_students])
    improved_students = set(rng.choice(remaining, size=12, replace=False).tolist())
    remaining = np.array([sid for sid in remaining if sid not in improved_students])
    risk_students = set(rng.choice(remaining, size=24, replace=False).tolist())
    remaining = np.array([sid for sid in remaining if sid not in risk_students])
    high_effort_low_accuracy = set(rng.choice(np.array(list(risk_students)), size=10, replace=False).tolist())
    low_submit_high_accuracy = set(rng.choice(remaining, size=10, replace=False).tolist())

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.executescript(
            """
            PRAGMA journal_mode=MEMORY;

            DROP TABLE IF EXISTS classes;
            DROP TABLE IF EXISTS students;
            DROP TABLE IF EXISTS knowledge_points;
            DROP TABLE IF EXISTS assignments;
            DROP TABLE IF EXISTS submissions;
            DROP TABLE IF EXISTS question_records;
            DROP TABLE IF EXISTS learning_sessions;
            DROP TABLE IF EXISTS interventions;

            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                grade TEXT NOT NULL,
                teacher_name TEXT NOT NULL
            );

            CREATE TABLE students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                class_id INTEGER NOT NULL,
                gender TEXT NOT NULL,
                enrollment_status TEXT NOT NULL,
                FOREIGN KEY (class_id) REFERENCES classes(id)
            );

            CREATE TABLE knowledge_points (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                subject TEXT NOT NULL
            );

            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                class_id INTEGER NOT NULL,
                knowledge_point_id INTEGER NOT NULL,
                assigned_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                week_index INTEGER NOT NULL,
                max_score REAL NOT NULL,
                FOREIGN KEY (class_id) REFERENCES classes(id),
                FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
            );

            CREATE TABLE submissions (
                id INTEGER PRIMARY KEY,
                assignment_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                submitted_at TEXT,
                status TEXT NOT NULL,
                score REAL,
                correct_rate REAL,
                time_spent_minutes REAL,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id),
                FOREIGN KEY (student_id) REFERENCES students(id)
            );

            CREATE TABLE question_records (
                id INTEGER PRIMARY KEY,
                assignment_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                knowledge_point_id INTEGER NOT NULL,
                question_no INTEGER NOT NULL,
                is_correct INTEGER NOT NULL,
                score REAL NOT NULL,
                answered_at TEXT NOT NULL,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
            );

            CREATE TABLE learning_sessions (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                week_index INTEGER NOT NULL,
                duration_minutes REAL NOT NULL,
                activity_type TEXT NOT NULL,
                engagement_score REAL NOT NULL,
                knowledge_point_id INTEGER,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
            );

            CREATE TABLE interventions (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                class_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                focus_area TEXT NOT NULL,
                action_suggestion TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (class_id) REFERENCES classes(id)
            );
            """
        )

        cursor.executemany(
            "INSERT INTO classes (id, name, grade, teacher_name) VALUES (?, ?, ?, ?)",
            [(item["id"], item["name"], item["grade"], item["teacher_name"]) for item in CLASS_CONFIG],
        )
        cursor.executemany(
            "INSERT INTO knowledge_points (id, name, subject) VALUES (?, ?, ?)",
            [(index, name, subject) for index, (name, subject) in enumerate(KNOWLEDGE_POINTS, start=1)],
        )

        student_rows = []
        student_ability: dict[int, float] = {}
        student_diligence: dict[int, float] = {}
        student_focus_kp: dict[int, int] = {}
        student_class: dict[int, int] = {}

        student_id = 1
        name_idx = 0
        for class_cfg, class_size in zip(CLASS_CONFIG, CLASS_SIZES):
            class_id = class_cfg["id"]
            for _ in range(class_size):
                name = student_names[name_idx]
                name_idx += 1
                gender = "女" if student_id % 2 == 0 else "男"
                student_rows.append((student_id, name, class_id, gender, "active"))
                base_ability = 0.67 + CLASS_ACCURACY_ADJUST[class_id] + rng.normal(0, 0.08)
                base_diligence = 0.8 + CLASS_SUBMISSION_ADJUST[class_id] + rng.normal(0, 0.08)
                if student_id in risk_students:
                    base_ability -= 0.08
                    base_diligence -= 0.1
                if student_id in improved_students:
                    base_ability -= 0.02
                    base_diligence += 0.02
                if student_id in decline_students:
                    base_diligence -= 0.04
                if student_id in low_submit_high_accuracy:
                    base_ability += 0.09
                    base_diligence -= 0.12
                if student_id in high_effort_low_accuracy:
                    base_ability -= 0.08
                    base_diligence += 0.08
                student_ability[student_id] = _clip(base_ability, 0.38, 0.92)
                student_diligence[student_id] = _clip(base_diligence, 0.4, 0.98)
                student_focus_kp[student_id] = int(rng.integers(1, len(KNOWLEDGE_POINTS) + 1))
                student_class[student_id] = class_id
                student_id += 1

        cursor.executemany(
            "INSERT INTO students (id, name, class_id, gender, enrollment_status) VALUES (?, ?, ?, ?, ?)",
            student_rows,
        )

        assignments = []
        assignment_id = 1
        today = date(2026, 6, 30)
        knowledge_plan = [1, 7, 3, 5, 2, 4, 8, 9, 6, 10, 11, 12]
        for class_cfg in CLASS_CONFIG:
            class_id = class_cfg["id"]
            for idx, week_index in enumerate(ASSIGNMENT_WEEKS):
                kp_id = knowledge_plan[idx]
                week_start = _week_start(today, week_index)
                assigned_date = week_start + timedelta(days=idx % 3)
                due_date = assigned_date + timedelta(days=2)
                title = f"{class_cfg['grade']}{class_cfg['name']}·第{week_index}周任务{idx + 1}"
                assignments.append(
                    (
                        assignment_id,
                        title,
                        class_id,
                        kp_id,
                        assigned_date.isoformat(),
                        due_date.isoformat(),
                        week_index,
                        100.0,
                    )
                )
                assignment_id += 1

        cursor.executemany(
            """
            INSERT INTO assignments (
                id, title, class_id, knowledge_point_id, assigned_date, due_date, week_index, max_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            assignments,
        )

        submissions = []
        question_records = []
        learning_sessions = []
        interventions = []
        submission_id = 1
        question_id = 1
        session_id = 1
        intervention_id = 1

        students_by_class: dict[int, list[int]] = {cfg["id"]: [] for cfg in CLASS_CONFIG}
        for sid, _, class_id, _, _ in student_rows:
            students_by_class[class_id].append(sid)

        for week_index in range(1, WEEKS + 1):
            week_start = _week_start(today, week_index)
            for sid in range(1, total_students + 1):
                class_id = student_class[sid]
                for offset in range(2):
                    duration = 38 + 28 * student_diligence[sid] + rng.normal(0, 8)
                    if sid in high_effort_low_accuracy:
                        duration += 25
                    if sid in low_submit_high_accuracy:
                        duration -= 10
                    engagement = 70 + 18 * student_diligence[sid] + 8 * CLASS_ENGAGEMENT_ADJUST[class_id] + rng.normal(0, 6)
                    learning_sessions.append(
                        (
                            session_id,
                            sid,
                            (week_start + timedelta(days=offset * 2 + 1)).isoformat(),
                            week_index,
                            round(_clip(duration, 15, 150), 1),
                            SESSION_TYPES[(sid + week_index + offset) % len(SESSION_TYPES)],
                            round(_clip(engagement, 45, 98), 1),
                            student_focus_kp[sid] if offset == 0 else int(rng.integers(1, len(KNOWLEDGE_POINTS) + 1)),
                        )
                    )
                    session_id += 1

        for assignment in assignments:
            assignment_id, _, class_id, kp_id, _, due_date, week_index, _ = assignment
            due_dt = datetime.combine(date.fromisoformat(due_date), time(19, 30))

            for sid in students_by_class[class_id]:
                submission_prob = 0.92 + CLASS_SUBMISSION_ADJUST[class_id] + (student_diligence[sid] - 0.8)
                if week_index in (7, 8) and class_id == 3:
                    submission_prob -= 0.18
                if sid in decline_students and week_index in (7, 8):
                    submission_prob -= 0.1
                if sid in low_submit_high_accuracy:
                    submission_prob -= 0.18
                if sid in improved_students and week_index in (7, 8):
                    submission_prob += 0.03
                if kp_id == 2:
                    submission_prob -= 0.02
                submitted = rng.random() < _clip(submission_prob, 0.45, 0.99)

                accuracy = student_ability[sid] + KNOWLEDGE_ACCURACY_ADJUST[kp_id] + rng.normal(0, 0.05)
                accuracy += 0.5 * CLASS_ACCURACY_ADJUST[class_id]
                if kp_id == 4 and class_id in (2, 5):
                    accuracy -= 0.08
                if sid in decline_students and week_index in (7, 8):
                    accuracy -= 0.14
                if sid in improved_students and week_index in (7, 8):
                    accuracy += 0.12
                if sid in risk_students:
                    accuracy -= 0.04
                if sid in high_effort_low_accuracy:
                    accuracy -= 0.09
                if sid in low_submit_high_accuracy:
                    accuracy += 0.08
                accuracy = _clip(accuracy, 0.22, 0.97)

                time_spent = 42 + accuracy * 24 + (student_diligence[sid] - 0.7) * 45 + rng.normal(0, 10)
                if sid in high_effort_low_accuracy:
                    time_spent += 35
                if sid in low_submit_high_accuracy:
                    time_spent -= 6
                time_spent = round(_clip(time_spent, 15, 180), 1)

                status = "submitted" if submitted else "missing"
                submitted_at = (due_dt - timedelta(hours=float(rng.uniform(0.5, 20)))).isoformat(timespec="minutes") if submitted else None
                score = round(accuracy * 100, 1) if submitted else None
                correct_rate = round(accuracy, 4) if submitted else None

                submissions.append((submission_id, assignment_id, sid, submitted_at, status, score, correct_rate, time_spent))

                if submitted:
                    for question_no in range(1, QUESTION_COUNT_PER_ASSIGNMENT + 1):
                        question_prob = _clip(accuracy + rng.normal(0, 0.05), 0.08, 0.99)
                        is_correct = 1 if rng.random() < question_prob else 0
                        answered_at = (due_dt - timedelta(hours=float(rng.uniform(0.2, 10)))).isoformat(timespec="minutes")
                        question_records.append(
                            (question_id, assignment_id, sid, kp_id, question_no, is_correct, 1.0 if is_correct else 0.0, answered_at)
                        )
                        question_id += 1

                submission_id += 1

        for sid in sorted(risk_students | set(list(decline_students)[:8])):
            class_id = student_class[sid]
            focus_area = KNOWLEDGE_POINTS[student_focus_kp[sid] - 1][0]
            if sid in high_effort_low_accuracy:
                action = f"学习时长较高但效果不佳，建议围绕 {focus_area} 做方法指导与错题归因。"
                level = "high"
            elif sid in low_submit_high_accuracy:
                action = f"能力基础尚可，但投入不足，建议对 {focus_area} 任务设置提交提醒。"
                level = "medium"
            elif sid in decline_students:
                action = f"最近两周表现下滑，建议本周围绕 {focus_area} 进行小组辅导。"
                level = "high"
            else:
                action = f"正确率与提交率均偏低，建议围绕 {focus_area} 安排补弱任务。"
                level = "high"
            interventions.append(
                (
                    intervention_id,
                    sid,
                    class_id,
                    datetime(2026, 6, 30, 10, 0).isoformat(timespec="minutes"),
                    level,
                    focus_area,
                    action,
                    "open",
                )
            )
            intervention_id += 1

        cursor.executemany(
            """
            INSERT INTO submissions (
                id, assignment_id, student_id, submitted_at, status, score, correct_rate, time_spent_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            submissions,
        )
        cursor.executemany(
            """
            INSERT INTO question_records (
                id, assignment_id, student_id, knowledge_point_id, question_no, is_correct, score, answered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            question_records,
        )
        cursor.executemany(
            """
            INSERT INTO learning_sessions (
                id, student_id, session_date, week_index, duration_minutes, activity_type, engagement_score, knowledge_point_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            learning_sessions,
        )
        cursor.executemany(
            """
            INSERT INTO interventions (
                id, student_id, class_id, created_at, risk_level, focus_area, action_suggestion, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            interventions,
        )
        conn.commit()
