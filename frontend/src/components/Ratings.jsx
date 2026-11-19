function ScoreBadge({ label, value, color }) {
  if (!value || value === "N/A") return null;
  return <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold ${color}`}><span className="opacity-70">{label}</span> {value}</span>;
}

export default function Ratings({ratings}) {
  if (!ratings) return null;
  return (
<div className="flex flex-wrap items-center gap-2 mt-2" data-testid="external-ratings">
                  <ScoreBadge label="RT" value={ratings.rotten_tomatoes} color="bg-rose-500/10 border-rose-500/30 text-rose-300" />
                  <ScoreBadge label="MC" value={ratings.metacritic} color="bg-emerald-500/10 border-emerald-500/30 text-emerald-300" />
                  <ScoreBadge label="IMDb" value={ratings.imdb} color="bg-amber-500/10 border-amber-500/30 text-amber-300" />
                </div>
  );
}
