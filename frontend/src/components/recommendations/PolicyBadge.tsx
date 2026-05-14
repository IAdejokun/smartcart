import { cn } from "../../lib/cn";
import { useAuthStore } from "../../store/authStore";

interface PolicyBadgeProps {
  policy: "drl" | "collab_filter" | "organic";
  className?: string;
}

const LABELS: Record<PolicyBadgeProps["policy"], string> = {
  drl: "DRL",
  collab_filter: "CF",
  organic: "—",
};

const STYLES: Record<PolicyBadgeProps["policy"], string> = {
  drl: "bg-brand-100 text-brand-700 border-brand-200",
  collab_filter: "bg-amber-100 text-amber-700 border-amber-200",
  organic: "bg-gray-100 text-gray-500 border-gray-200",
};

export function PolicyBadge({ policy, className }: PolicyBadgeProps) {
  const user = useAuthStore((s) => s.user);
  if (!user) return null; // hide from anonymous visitors

  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 text-[10px] font-semibold rounded border uppercase tracking-wide",
        STYLES[policy],
        className,
      )}
      title={`Recommendation policy: ${policy}`}
    >
      {LABELS[policy]}
    </span>
  );
}
