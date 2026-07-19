import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AgentChart } from "../api";

type ChartCardProps = {
  title: string;
  subtitle?: string;
  type: "bar" | "line";
  data: Array<Record<string, string | number>>;
  xKey: string;
  yKey?: string;
  series?: string[];
  panelClassName?: string;
  chartHeightClass?: string;
};

function pivotSeries(data: Array<Record<string, string | number>>, xKey: string, series: string[]) {
  const group = new Map<string, Record<string, string | number>>();
  data.forEach((item) => {
    const xValue = String(item[xKey]);
    const groupName = String(item.class_name);
    const yValue = Number(item.submission_rate);
    if (!group.has(xValue)) group.set(xValue, { [xKey]: xValue });
    group.get(xValue)![groupName] = yValue;
  });
  return Array.from(group.values()).map((item) => {
    series.forEach((name) => {
      if (!(name in item)) item[name] = 0;
    });
    return item;
  });
}

export default function ChartCard({
  title,
  subtitle,
  type,
  data,
  xKey,
  yKey,
  series,
  panelClassName,
  chartHeightClass,
}: ChartCardProps) {
  const palette = ["#5f79ff", "#14b8a6", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];
  const hasMultiSeries = Boolean(series && series.length > 1);
  const chartData = hasMultiSeries ? pivotSeries(data, xKey, series ?? []) : data;

  return (
    <div className={`panel flex flex-col p-5 ${panelClassName ?? ""}`}>
      <div className="mb-5">
        <h3 className="panel-title">{title}</h3>
        {subtitle && <p className="panel-subtitle mt-1">{subtitle}</p>}
      </div>
      <div className={chartHeightClass ?? "h-[320px]"}>
        <ResponsiveContainer width="100%" height="100%">
          {type === "bar" ? (
            <BarChart data={chartData} margin={{ left: 4, right: 8, top: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey={xKey} tick={{ fill: "#64748b", fontSize: 12 }} interval={0} angle={chartData.length > 8 ? -20 : 0} height={chartData.length > 8 ? 56 : 36} />
              <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey={yKey ?? ""} fill="#5f79ff" radius={[6, 6, 0, 0]} />
            </BarChart>
          ) : (
            <LineChart data={chartData} margin={{ left: 4, right: 8, top: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey={xKey} tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
              <Tooltip />
              {hasMultiSeries ? (
                <>
                  <Legend />
                  {(series ?? []).map((item, index) => (
                    <Line key={item} type="monotone" dataKey={item} stroke={palette[index % palette.length]} strokeWidth={2.5} dot={{ r: 3 }} />
                  ))}
                </>
              ) : (
                <Line type="monotone" dataKey={yKey ?? ""} stroke="#5f79ff" strokeWidth={2.5} dot={{ r: 3 }} />
              )}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function AgentChartCard({ chart }: { chart: AgentChart }) {
  if (chart.type === "table" || chart.data.length === 0) return null;
  return (
    <ChartCard
      title={chart.title}
      subtitle="系统已根据当前查询自动生成配套图表"
      type={chart.type === "pie" ? "bar" : chart.type}
      data={chart.data as Array<Record<string, string | number>>}
      xKey={chart.x_field}
      yKey={chart.y_field ?? undefined}
      series={chart.series}
    />
  );
}
