import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EntropyPoint } from "../../types/api";

interface EntropyChartProps {
  data: EntropyPoint[];
}

export function EntropyChart({ data }: EntropyChartProps) {
  const chartData = data.map((p) => ({
    time: p.bucket_start
      ? new Date(p.bucket_start).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "",
    entropy: p.entropy_proxy,
    distinct: p.distinct_top_products,
  }));

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold mb-1">Recommendation diversity</h2>
      <p className="text-xs text-gray-500 mb-4">
        Distinct top recommendations per time bucket · proxy for agent
        exploration
      </p>

      {chartData.length === 0 ? (
        <div className="text-center text-sm text-gray-400 py-8">
          Not enough data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="entropyGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0d9488" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#0d9488" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #e5e7eb",
                fontSize: 12,
              }}
            />
            <Area
              type="monotone"
              dataKey="entropy"
              stroke="#0d9488"
              strokeWidth={2}
              fill="url(#entropyGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
