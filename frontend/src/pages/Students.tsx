import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { api, StudentListItem, StudentProfileResponse } from "../api";
import { useLayoutContext } from "../components/Layout";
import StudentProfile from "../components/StudentProfile";

export default function Students() {
  const { selectedClassId } = useLayoutContext();
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [profile, setProfile] = useState<StudentProfileResponse | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.getStudents(selectedClassId).then((payload) => {
      setStudents(payload);
      setSelectedStudentId((current) => (payload.some((item) => item.id === current) ? current : payload[0]?.id ?? null));
    });
  }, [selectedClassId]);

  useEffect(() => {
    if (!selectedStudentId) return;
    api.getStudentProfile(selectedStudentId).then(setProfile).catch(() => undefined);
  }, [selectedStudentId]);

  const filteredStudents = useMemo(() => students.filter((item) => item.name.includes(search)), [students, search]);

  return (
    <div className="grid gap-6 xl:grid-cols-[320px,1fr]">
      <aside className="panel overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="panel-title">学生画像列表</h3>
          <p className="panel-subtitle mt-1">按班级查看学生个体趋势、风险标签和个性化建议</p>
          <div className="relative mt-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索学生姓名"
              className="h-11 w-full rounded-lg border border-slate-200 bg-slate-50 pl-10 pr-3 text-sm outline-none transition focus:border-accent-500 focus:bg-white"
            />
          </div>
        </div>
        <div className="max-h-[760px] overflow-y-auto p-3">
          {filteredStudents.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelectedStudentId(item.id)}
              className={`mb-2 w-full rounded-lg border px-4 py-3 text-left transition ${selectedStudentId === item.id ? "border-accent-500 bg-accent-50" : "border-transparent bg-white hover:border-slate-200 hover:bg-slate-50"}`}
            >
              <p className="text-sm font-medium text-slate-900">{item.name}</p>
              <p className="mt-1 text-xs text-slate-500">{item.class_name}</p>
            </button>
          ))}
          {!filteredStudents.length && <div className="rounded-lg border border-dashed border-slate-200 px-4 py-5 text-sm text-slate-500">当前筛选范围内没有匹配学生</div>}
        </div>
      </aside>

      <section>{profile ? <StudentProfile data={profile} /> : <div className="panel p-5 text-sm text-slate-500">正在加载学生画像...</div>}</section>
    </div>
  );
}
