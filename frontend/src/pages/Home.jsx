import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Info, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { MediaGrid, CardSkeleton } from "@/components/MediaCard";
import Pagination from "@/components/Pagination";

export default function Home() {
  const { type } = useParams();
  const isBrowse = !!type;
  const [page, setPage] = useState(1);

  useEffect(() => { setPage(1); window.scrollTo(0, 0); }, [type]);

  const { data, isLoading } = useQuery({
    queryKey: ["home", type || "trending", page],
    queryFn: () => (isBrowse ? api.discover(type, page) : api.trending()),
    keepPreviousData: true,
  });

  const items = data?.results || [];
  const hero = !isBrowse ? items.find((i) => i.backdrop) : null;
  const title = isBrowse ? (type === "series" ? "TV Shows" : "Movies") : "Discover";

  const goto = (p) => { setPage(p); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return (
    <div className="pb-16">
      {hero && (
        <section className="relative h-[52vh] min-h-[380px] w-full overflow-hidden">
          <img src={hero.backdrop} alt={hero.title} className="absolute inset-0 w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#050507] via-[#050507]/70 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#050507] via-transparent to-transparent" />
          <div className="relative z-10 h-full flex flex-col justify-end p-6 md:p-12 max-w-3xl">
            <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-blue-300 mb-3">
              <TrendingUp size={13} /> Trending this week
            </div>
            <h1 className="font-heading text-4xl md:text-6xl font-extrabold tracking-tighter metallic-text leading-none">{hero.title}</h1>
            <p className="mt-4 text-sm md:text-base text-slate-300 line-clamp-3 max-w-xl">{hero.overview}</p>
            <div className="mt-6 flex items-center gap-3">
              <Link to={`/title/${hero.media_type}/${hero.id}`} data-testid="hero-view-btn"
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-6 py-3 text-sm font-bold text-white hover:brightness-110 transition-[filter] shadow-[0_6px_24px_rgba(59,130,246,0.4)]">
                <Zap size={16} /> Find Sources
              </Link>
              <Link to={`/title/${hero.media_type}/${hero.id}`}
                className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 backdrop-blur px-5 py-3 text-sm font-semibold text-slate-100 hover:bg-white/10 transition-colors">
                <Info size={16} /> Details
              </Link>
            </div>
          </div>
        </section>
      )}

      <section className="px-4 md:px-12 mt-8">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-heading text-2xl md:text-3xl font-bold tracking-tight text-white">
            {isBrowse ? title : "Popular Right Now"}
          </h2>
          {isBrowse && data && <span className="text-sm text-slate-500">Page {data.page} of {Math.min(data.total_pages, 500)}</span>}
        </div>
        {isLoading ? <CardSkeleton /> : <MediaGrid items={items} />}
        {isBrowse && data && <Pagination page={data.page} totalPages={data.total_pages} onChange={goto} />}
      </section>
    </div>
  );
}
