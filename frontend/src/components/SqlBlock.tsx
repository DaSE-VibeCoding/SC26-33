import { Copy } from "lucide-react";
import { useState } from "react";

type SqlBlockProps = {
  sql: string;
};

export default function SqlBlock({ sql }: SqlBlockProps) {
  const [copied, setCopied] = useState(false);

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
        <div>
          <h3 className="panel-title">SQL 代码</h3>
          <p className="panel-subtitle mt-1">系统生成并通过安全校验后的只读查询语句</p>
        </div>
        <button
          type="button"
          onClick={async () => {
            await navigator.clipboard.writeText(sql);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1200);
          }}
          className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm text-slate-600 transition hover:bg-slate-50"
        >
          <Copy size={16} />
          {copied ? "已复制" : "复制 SQL"}
        </button>
      </div>
      <pre className="overflow-x-auto bg-slate-950 px-5 py-5 text-sm leading-6 text-slate-100">
        <code>{sql}</code>
      </pre>
    </div>
  );
}