from __future__ import annotations

import re


ALLOWED_TABLES = {
    "classes",
    "students",
    "knowledge_points",
    "assignments",
    "submissions",
    "question_records",
    "learning_sessions",
    "interventions",
}

DANGEROUS_KEYWORDS = {
    "drop",
    "delete",
    "update",
    "insert",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
}


def strip_sql_comments(sql: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    without_line = re.sub(r"--.*?$", " ", without_block, flags=re.M)
    return without_line


def _extract_cte_names(sql: str) -> set[str]:
    if not re.match(r"^\s*with\b", sql, flags=re.I):
        return set()
    return {match.lower() for match in re.findall(r"\b([a-zA-Z_][\w]*)\s+as\s*\(", sql, flags=re.I)}


def _extract_table_names(sql: str) -> set[str]:
    return {match.lower() for match in re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w]*)", sql, flags=re.I)}


def validate_select_sql(sql: str, allowed_tables: set[str] | None = None) -> str:
    allowed = allowed_tables or ALLOWED_TABLES
    cleaned = strip_sql_comments(sql).strip()
    if not cleaned:
        raise ValueError("未生成可执行查询。")

    semicolon_count = cleaned.count(";")
    if semicolon_count > 1:
        raise ValueError("仅允许执行单条 SQL 查询。")
    if semicolon_count == 1 and not cleaned.endswith(";"):
        raise ValueError("检测到分号后追加语句，系统已拒绝执行。")
    if ";" in cleaned:
        cleaned = cleaned[:-1].strip()

    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("仅允许执行 SELECT / WITH 只读查询。")

    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            raise ValueError("检测到危险 SQL 关键字，系统已拒绝执行。")

    cte_names = _extract_cte_names(cleaned)
    referenced_tables = _extract_table_names(cleaned)
    illegal_tables = sorted(table for table in referenced_tables if table not in allowed and table not in cte_names)
    if illegal_tables:
        raise ValueError(f"查询引用了未授权的数据表: {', '.join(illegal_tables)}")

    return cleaned
