interface Props {
  relevant: boolean;
  count: number;
}

export function MetaBadge({ relevant, count }: Props) {
  if (relevant) {
    return (
      <div className="flex items-center gap-3">
        <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-semibold text-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          META RELEVANT
        </span>
        <span className="text-[#888888] text-sm">
          Found in <span className="text-[#111111] font-medium">{count}</span> tournament deck{count !== 1 ? "s" : ""}
        </span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-3">
      <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-50 border border-red-200 text-red-700 font-semibold text-sm">
        <span className="w-2 h-2 rounded-full bg-red-500" />
        NOT IN RECENT META
      </span>
      <span className="text-[#888888] text-sm">No tournament appearances found</span>
    </div>
  );
}
