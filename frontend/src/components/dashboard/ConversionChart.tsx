import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PolicyComparison } from "../../types/api";
import { formatPercent } from "../../lib/format";

interface ConversionChartProps {
  data: PolicyComparison;
}

// Recharts tooltip formatter receives `ValueType` which is broader than number.
// We narrow at the call site and fall through to a dash for unexpected types.
function formatPercentValue(value: unknown): string {
  return typeof value === "number" ? formatPercent(value, 2) : "—";
}

export function ConversionChart({ data }: ConversionChartProps) {
  const chartData = [
    {
      policy: "DRL",
      rate: data.policies.drl.rate,
      shown: data.policies.drl.shown,
      converted: data.policies.drl.converted,
    },
    {
      policy: "CF Baseline",
      rate: data.policies.collab_filter.rate,
      shown: data.policies.collab_filter.shown,
      converted: data.policies.collab_filter.converted,
    },
  ];

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold mb-1">
        Conversion rate by policy
      </h2>
      <p className="text-xs text-gray-500 mb-4">
        Add-to-cart rate per recommendation served · {data.window}
      </p>

      <ResponsiveContainer width="100%" height={240}>
        <BarChart
          data={chartData}
          margin={{ top: 16, right: 16, bottom: 0, left: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="policy" tick={{ fontSize: 12 }} />
          <YAxis
            domain={[0, 1]} // ← lock to 0%-100%
            tickFormatter={(v) =>
              typeof v === "number" ? `${(v * 100).toFixed(0)}%` : ""
            }
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={formatPercentValue}
            contentStyle={{
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar
            dataKey="rate"
            fill="#0d9488"
            radius={[6, 6, 0, 0]}
            name="Conversion rate"
          />
        </BarChart>
      </ResponsiveContainer>

      <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
        <StatCell
          label="DRL"
          shown={data.policies.drl.shown}
          converted={data.policies.drl.converted}
        />
        <StatCell
          label="CF"
          shown={data.policies.collab_filter.shown}
          converted={data.policies.collab_filter.converted}
        />
      </div>
    </div>
  );
}

function StatCell({
  label,
  shown,
  converted,
}: {
  label: string;
  shown: number;
  converted: number;
}) {
  return (
    <div className="bg-gray-50 rounded-lg px-3 py-2">
      <span className="text-xs text-gray-500 uppercase tracking-wide">
        {label}
      </span>
      <div className="flex items-baseline gap-1.5 mt-0.5">
        <span className="font-semibold">{converted}</span>
        <span className="text-xs text-gray-500">/ {shown} shown</span>
      </div>
    </div>
  );
}
