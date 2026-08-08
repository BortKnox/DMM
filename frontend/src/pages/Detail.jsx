import { useState, useMemo, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Star, Clock, ArrowLeft, Zap, Filter, Loader2, Layers, ChevronDown, LayoutGrid, List, DownloadCloud } from "lucide-react";
import { api } from "@/lib/api";
import SourceRow from "@/components/SourceRow";

const RES_CHIPS = ["2160p", "1080p", "720p", "480p"];

function ScoreBadge({ label, value, color }) {
  if (!value || value === "N/A") return null;
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold ${color}`}>
      <span className="opacity-70">{label}</span> {value}
    </span>
  );
}

export default function Detail() {
  const { mediaType, tmdbId } = useParams();
  const [season, setSeason] = useState(1);
  const [episode, setEpisode] = useState(1);
  const [filter, setFilter] = useState("");
  const [resChip, setResChip] = useState(null);
  const [cachedOnly, setCachedOnly] = useState(false);
  const [view, setView] = useState("list");
  const [caching, setCaching] = useState(false);

  const { data: meta, isLoading: metaLoading } = useQuery({
    queryKey: ["meta", mediaType, tmdbId],
    queryFn: () => api.meta(mediaType, tmdbId),
  });

  const isSeries = mediaType === "series";

  const { data: seasonData } = useQuery({
    queryKey: ["season", tmdbId, season],
    queryFn: () => api.season(tmdbId, season),
    enabled: isSeries && !!meta,
  });

  const sourceParams = isSeries
    ? { media_type: "series", season, episode, title: meta?.title }
    : { media_type: "movie", title: meta?.title };

  const { data: sourcesData, isFetching: sourcesLoading } = useQuery({
    queryKey: ["sources", meta?.imdb_id, sourceParams.media_type, season, episode],
    queryFn: () => api.sources(meta.imdb_id, sourceParams),
    enabled: !!meta?.imdb_id,
  });

  useEffect(() => { setEpisode(1); }, [season]);

  const sources = sourcesData?.sources || [];
  const filtered = useMemo(() => {
    let list = sources;
    if (cachedOnly) list = list.filter((s) => s.cached);
    if (resChip) list = list.filter((s) => s.quality?.resolution === resChip);
    if (filter.trim()) {
      try { const re = new RegExp(filter, "i"); list = list.filter((s) => re.test(s.name)); }
      catch { list = list.filter((s) => s.name.toLowerCase().includes(filter.toLowerCase())); }
    }
    return list;
  }, [sources, filter, resChip, cachedOnly]);

  const currentSeason = (meta?.seasons || []).find((s) => s.season_number === season);

  const cacheSeason = async () => {
    if (!currentSeason) return;
    setCaching(true);
    toast.info(`Caching Season ${season}… this can take a moment`);
    try {
      const res = await api.cacheSeason({ imdb_id: meta.imdb_id, season, episodes: currentSeason.episode_count, title: meta.title });
      toast.success(`Season ${season}: sent ${res.added}/${res.episodes_found} episodes to TorBox`);
    } catch { toast.error("Bulk cache failed"); } finally { setCaching(false); }
  };

  if (metaLoading || !meta) {
    return <div className="p-12 flex justify-center"><Loader2 className="animate-spin text-blue-500" size={32} /></div>;
  }

  return (
    <div className="pb-20">
      <section className="relative h-[46vh] min-h-[340px] w-full overflow-hidden">
        {meta.backdrop && <img src={meta.backdrop} alt={meta.title} className="absolute inset-0 w-full h-full object-cover" />}
        <div className="absolute inset-0 bg-gradient-to-t from-[#050507] via-[#050507]/60 to-[#050507]/30" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#050507]/80 to-transparent" />
        <div className="relative z-10 h-full flex items-end p-4 md:p-12">
          <Link to="/" className="absolute top-4 left-4 md:top-6 md:left-6 inline-flex items-center gap-1.5 rounded-full bg-black/50 backdrop-blur border border-white/10 px-3 py-1.5 text-xs text-slate-200 hover:bg-black/70 transition-colors" data-testid="back-btn">
            <ArrowLeft size={14} /> Back
          </Link>
          <div className="flex gap-5 items-end max-w-4xl">
            {meta.poster && <img src={meta.poster} alt={meta.title} className="hidden sm:block w-28 md:w-40 rounded-lg border border-white/10 shadow-2xl" />}
            <div>
              {meta.logo ? (
                <img src={meta.logo} alt={meta.title} className="max-h-24 max-w-[70%] object-contain drop-shadow-lg mb-1" />
              ) : (
                <h1 className="font-heading text-3xl md:text-5xl font-extrabold tracking-tighter text-white leading-none">{meta.title}</h1>
              )}
              {meta.tagline && <p className="italic text-slate-400 text-sm mt-2">{meta.tagline}</p>}
              <div className="flex flex-wrap items-center gap-2 mt-3 text-xs text-slate-300">
                <span className="inline-flex items-center gap-1 text-amber-300"><Star size={13} className="fill-amber-300" /> {meta.rating}</span>
                <span>{meta.year}</span>
                {meta.runtime && <span className="inline-flex items-center gap-1"><Clock size={12} /> {meta.runtime}m</span>}
                {meta.rated && <span className="rounded border border-white/20 px-1.5 py-0.5 text-[10px]">{meta.rated}</span>}
                {(meta.genres || []).slice(0, 3).map((g) => <span key={g} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5">{g}</span>)}
              </div>
              {meta.ratings && (
                <div className="flex flex-wrap items-center gap-2 mt-2" data-testid="external-ratings">
                  <ScoreBadge label="RT" value={meta.ratings.rotten_tomatoes} color="bg-rose-500/10 border-rose-500/30 text-rose-300" />
                  <ScoreBadge label="MC" value={meta.ratings.metacritic} color="bg-emerald-500/10 border-emerald-500/30 text-emerald-300" />
                  <ScoreBadge label="IMDb" value={meta.ratings.imdb} color="bg-amber-500/10 border-amber-500/30 text-amber-300" />
                </div>
              )}
              <p className="mt-3 text-sm text-slate-300 line-clamp-2 max-w-2xl">{meta.overview}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="px-4 md:px-12 mt-8">
        {isSeries && (
          <div className="mb-6 flex flex-wrap items-end gap-4">
            <div>
              <label className="text-[11px] uppercase tracking-[0.2em] text-slate-500 flex items-center gap-1 mb-1.5"><Layers size={12} /> Season</label>
              <div className="relative">
                <select data-testid="season-select" value={season} onChange={(e) => setSeason(Number(e.target.value))}
                  className="appearance-none bg-white/5 border border-white/10 rounded-lg pl-3 pr-9 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                  {(meta.seasons || []).map((s) => <option key={s.season_number} value={s.season_number} className="bg-[#0C0D12]">Season {s.season_number} ({s.episode_count} eps)</option>)}
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
              </div>
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-[0.2em] text-slate-500 mb-1.5 block">Episode</label>
              <div className="relative">
                <select data-testid="episode-select" value={episode} onChange={(e) => setEpisode(Number(e.target.value))}
                  className="appearance-none bg-white/5 border border-white/10 rounded-lg pl-3 pr-9 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                  {(seasonData?.episodes || [{ episode_number: 1, name: "Episode 1" }]).map((e) => <option key={e.episode_number} value={e.episode_number} className="bg-[#0C0D12]">E{e.episode_number} · {e.name}</option>)}
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
              </div>
            </div>
            <button data-testid="cache-season-btn" onClick={cacheSeason} disabled={caching}
              className="inline-flex items-center gap-2 rounded-full bg-blue-500/15 border border-blue-500/40 px-4 py-2 text-sm font-semibold text-blue-200 hover:bg-blue-500/25 transition-colors disabled:opacity-60">
              {caching ? <Loader2 size={15} className="animate-spin" /> : <DownloadCloud size={15} />} Cache Season {season}
            </button>
          </div>
        )}

        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <h2 className="font-heading text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Available Sources
            {sourcesData && <span className="text-sm font-normal text-slate-500">· {sourcesData.total} found · <span className="text-emerald-400">{sourcesData.cached_count} cached</span></span>}
          </h2>
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1">
            <button data-testid="view-list" onClick={() => setView("list")} className={`rounded-full p-1.5 transition-colors ${view === "list" ? "bg-blue-500/30 text-blue-200" : "text-slate-500 hover:text-slate-300"}`}><List size={15} /></button>
            <button data-testid="view-grid" onClick={() => setView("grid")} className={`rounded-full p-1.5 transition-colors ${view === "grid" ? "bg-blue-500/30 text-blue-200" : "text-slate-500 hover:text-slate-300"}`}><LayoutGrid size={15} /></button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-5">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input data-testid="source-filter-input" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter results (supports regex)…"
              className="w-full bg-white/5 border border-white/10 rounded-full pl-9 pr-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
          </div>
          <button data-testid="cached-only-toggle" onClick={() => setCachedOnly((v) => !v)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-2 text-xs font-semibold transition-colors ${cachedOnly ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300" : "bg-white/5 border-white/10 text-slate-400 hover:text-slate-200"}`}>
            <Zap size={13} /> Cached only
          </button>
          {RES_CHIPS.map((r) => (
            <button key={r} data-testid={`res-chip-${r}`} onClick={() => setResChip((v) => (v === r ? null : r))}
              className={`rounded-full border px-3 py-2 text-xs font-semibold transition-colors ${resChip === r ? "bg-blue-500/15 border-blue-500/40 text-blue-300" : "bg-white/5 border-white/10 text-slate-400 hover:text-slate-200"}`}>{r}</button>
          ))}
        </div>

        {sourcesLoading ? (
          <div className={view === "grid" ? "grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3" : "space-y-2"}>
            {Array.from({ length: view === "grid" ? 8 : 6 }).map((_, i) => <div key={i} className={`${view === "grid" ? "h-40" : "h-20"} rounded-lg skeleton`} />)}
          </div>
        ) : filtered.length ? (
          view === "grid" ? (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3" data-testid="sources-list">
              {filtered.map((s) => <SourceRow key={s.hash} source={s} mediaContext={isSeries ? { season, episode } : null} compact />)}
            </div>
          ) : (
            <div className="space-y-2" data-testid="sources-list">
              {filtered.map((s) => <SourceRow key={s.hash} source={s} mediaContext={isSeries ? { season, episode } : null} />)}
            </div>
          )
        ) : (
          <div className="py-16 text-center text-slate-500" data-testid="sources-empty">No sources match your filters.</div>
        )}
      </div>
    </div>
  );
}
