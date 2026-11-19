import { useEffect, useRef } from "react";
import SaveTitle from "@/components/SaveTitle";
import { usePosterSize } from "@/components/PosterSize";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Star, Film, Tv } from "lucide-react";
import { api } from "@/lib/api";

export function MediaCard({ item, index = 0 }) {
  const qc = useQueryClient();
  const timer = useRef();
  const cancel = () => clearTimeout(timer.current);
  useEffect(() => () => clearTimeout(timer.current), [item.id, item.media_type]);
  const warm = () => {
    cancel();
    timer.current = setTimeout(() => {
    qc.prefetchQuery({ queryKey: ["meta", item.media_type, String(item.id)], queryFn: () => api.meta(item.media_type, item.id), staleTime: 60000 });
    }, 200);
  };
  return (
    <div className="relative"><Link
      to={`/title/${item.media_type}/${item.id}`}
      onMouseEnter={warm}
      onFocus={warm}
      onMouseLeave={cancel}
      onBlur={cancel}
      data-testid={`media-card-${item.id}`}
      className="group relative block fade-up"
      style={{ animationDelay: `${Math.min(index * 40, 400)}ms` }}
    >
      <div className="relative aspect-[2/3] rounded-lg overflow-hidden bg-[#0C0D12] border border-white/5 group-hover:border-blue-500/40 transition-colors duration-300 shadow-[0_8px_24px_rgba(0,0,0,0.3)]">
        {item.poster ? (
          <img
            src={item.poster}
            alt={item.title}
            loading="lazy"
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-600">
            {item.media_type === "series" ? <Tv size={32} /> : <Film size={32} />}
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/10 to-transparent opacity-90" />
        <div className="absolute top-2 left-2 flex items-center gap-1 rounded-md bg-black/60 backdrop-blur-sm border border-white/10 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">
          <Star size={10} className="fill-amber-300 text-amber-300" /> {item.rating || "–"}
        </div>
        <div className="absolute top-9 left-2 rounded-md bg-blue-500/20 border border-blue-400/30 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-blue-200">
          {item.media_type === "series" ? "TV" : "Film"}
        </div>
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <h3 className="font-heading font-semibold text-sm text-white leading-tight line-clamp-2 drop-shadow">
            {item.title}
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">{item.year}</p>
        </div>
      </div>
    </Link><div className="poster-corner"><SaveTitle id={item.id} type={item.media_type} title={item.title}/></div></div>
  );
}

export function MediaGrid({ items }) {
  const posters = usePosterSize();
  return (
    <><div className="mb-3">{posters.control}</div><div style={posters.style} className="gap-4">
      {items.map((it, i) => (
        <MediaCard key={`${it.media_type}-${it.id}`} item={it} index={i} />
      ))}
    </div></>
  );
}

export function CardSkeleton({ count = 14 }) {
  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="aspect-[2/3] rounded-lg skeleton" />
      ))}
    </div>
  );
}
