# EduInsight

## 小组成员与贡献说明

本项目由小组成员共同完成，成员贡献度平均。

| 姓名 | 学号 | 贡献说明 |
| --- | --- | --- |
| 郑一钒 | 51285903070 | 平均贡献 |
| 张笑铖 | 51285903072 | 平均贡献 |
| 徐佳睿 | 51285903026 | 平均贡献 |
| 曲馥诺 | 51285903031 | 平均贡献 |
| 黄博 | 51285903030 | 平均贡献 |

EduInsight 是一个面向教师的自然语言学情分析 Data Agent Demo。教师可以用中文直接提问，系统会完成问题理解、数据查询、学习分析、图表展示和教学建议生成。

项目题目：

- 中文题目：EduInsight：基于大语言模型与学习分析的教师侧自然语言学情诊断系统
- 英文题目：EduInsight: A Teacher-facing Natural Language Learning Analytics Data Agent

## 功能概览

- 教师侧 Dashboard：展示班级正确率、提交率、风险学生、退步学生和知识点掌握情况。
- 自然语言 Data Agent：支持通过中文问题查询学情，并返回关键发现、图表证据、明细表格和教学建议。
- 学生画像：查看学生趋势、风险标签、薄弱知识点和个性化建议。
- 混合 Agent 链路：高频问题优先走本地 intent/SQL 模板，保证演示稳定；配置 API Key 后可启用 LLM Text-to-SQL 增强。
- SQL 安全校验：只允许只读查询，并拦截删除、修改表结构等危险请求。

## 技术栈

前端：

- Vite
- React + TypeScript
- Tailwind CSS
- Recharts
- lucide-react

后端：

- FastAPI
- SQLite
- pandas / numpy
- pydantic
- uvicorn
- openai Python SDK（用于 OpenAI-compatible API 接口）

## 项目结构

```text
edu-insight/
  README.md
  run_all.ps1
  backend/
    requirements.txt
    app/
      main.py
      db.py
      agent.py
      llm.py
      prompts.py
      sql_guard.py
      schemas.py
      analytics_service.py
      mock_seed_data.py
      data_agent.py
  frontend/
    package.json
    src/
      api.ts
      components/
      pages/
```

## 快速启动

在 Windows PowerShell 中执行：

```powershell
.\run_all.ps1
```

默认访问地址：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:5173`

## 后端启动

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

健康检查：

```powershell
curl http://127.0.0.1:8000/api/health
```

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

## LLM API 配置

不要把 API Key 写入代码、README、前端、日志或任何提交文件。系统只从环境变量读取：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`，默认 `deepseek-v4-flash`
- `DEEPSEEK_BASE_URL`，默认 `https://api.deepseek.com`

Windows PowerShell 设置示例：

```powershell
$env:DEEPSEEK_API_KEY="your_api_key"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

关闭在线模式：

```powershell
Remove-Item Env:DEEPSEEK_API_KEY
```

模式说明：

- 无 Key：系统进入离线演示模式，使用本地模板链路完成核心查询。
- 有 Key：系统进入在线增强模式，未知问题优先走 LLM Text-to-SQL 与总结增强。

## Mock 数据

系统会使用本地 SQLite mock 数据。数据库文件未提交到仓库时，后端会在需要时自动生成演示数据。

数据规模：

- 6 个班级
- 约 239 名学生
- 12 个知识点
- 8 周学习记录
- 12 次作业
- 2868 条提交记录
- 15138 条答题记录
- 3824 条学习行为记录

内置可分析模式：

- 七年级 3 班最近两周提交率下降
- 二次函数整体正确率偏低
- 几何证明在部分班级错误率偏高
- 部分学生最近两周退步明显
- 部分学生属于高风险学生
- 部分学生进步明显
- 部分学生学习时长高但正确率低
- 部分学生提交率低但正确率不低

## 重置 Mock 数据

方式 1：调用接口

```powershell
curl -Method POST http://127.0.0.1:8000/api/reset-demo-data
```

方式 2：执行后端重置逻辑

```powershell
cd backend
python -c "from app.db import reset_database; print(reset_database())"
```

## 开发者模式

教师界面默认不展示 SQL。如果需要查看 Text-to-SQL 或调试链路：

1. 打开 Data Agent 页面
2. 勾选“开发者模式”
3. 再次提交问题
4. 页面会显示 `debug` 信息和对应 SQL

## 示例问题

1. 这周哪些学生退步明显？
2. 哪个知识点错误率最高？
3. 帮我找出需要重点辅导的学生。
4. 生成一份本周班级学情报告。
5. 七年级 3 班最近作业提交率怎么样？
6. 哪些学生在二次函数上掌握较弱？
7. 学习时长很高但正确率低的学生有哪些？
8. 最近进步最大的学生是谁？
9. 哪个班级风险学生最多？
10. 几何证明这个知识点在哪些班问题比较严重？

危险请求验证：

```text
删除所有学生数据
DROP TABLE students
```

这些请求会被 SQL 安全层拒绝，不会执行。
