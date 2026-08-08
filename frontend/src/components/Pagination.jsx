import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({ page, totalPages, onChange }) {
  if (!totalPages || totalPages <= 1) return null;
  const max = Math.min(totalPages, 500);
  const win = 2;
  let start = Math.max(1, page - win);
  let end = Math.min(max, page + win);
  if (page <= win) end = Math.min(max, 1 + win * 2);
  if (page > max - win) start = Math.max(1, max - win * 2);
  const nums = [];
  for (let i = start; i <= end; i++) nums.push(i);

  const Btn = ({ children, onClick, active, disabled, testid }) => (
    <button
      data-testid={testid}
      onClick={onClick}
      disabled={disabled}
      className={`min-w-[38px] h-9 px-3 rounded-lg text-sm font-semibold transition-colors border ${
        active
          ? "bg-blue-500/20 border-blue-500/50 text-blue-200"
          : "bg-white/5 border-white/10 text-slate-400 hover:text-slate-100 hover:bg-white/10 disabled:opacity-40 disabled:hover:bg-white/5"
      }`}
    >
      {children}
    </button>
  );

  return (
    <div className="flex items-center justify-center gap-1.5 mt-10" data-testid="pagination">
      <Btn testid="page-prev" onClick={() => onChange(page - 1)} disabled={page <= 1}><ChevronLeft size={16} /></Btn>
      {start > 1 && (<><Btn testid="page-1" onClick={() => onChange(1)}>1</Btn>{start > 2 && <span className="text-slate-600 px-1">…</span>}</>)}
      {nums.map((n) => (
        <Btn key={n} testid={`page-${n}`} onClick={() => onChange(n)} active={n === page}>{n}</Btn>
      ))}
      {end < max && (<>{end < max - 1 && <span className="text-slate-600 px-1">…</span>}<Btn testid={`page-${max}`} onClick={() => onChange(max)}>{max}</Btn></>)}
      <Btn testid="page-next" onClick={() => onChange(page + 1)} disabled={page >= max}><ChevronRight size={16} /></Btn>
    </div>
  );
}
