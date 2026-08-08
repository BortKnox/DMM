import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { SearchX } from "lucide-react";
import { api } from "@/lib/api";
import { MediaGrid, CardSkeleton } from "@/components/MediaCard";
import Pagination from "@/components/Pagination";

export default function SearchResults() {
  const [params] = useSearchParams();
  const q = params.get("q") || "";
  const [page, setPage] = useState(1);

  useEffect(() => { setPage(1); }, [q]);

  const { data, isLoading } = useQuery({
    queryKey: ["search", q, page],
    queryFn: () => api.search(q, page),
    enabled: !!q,
    keepPreviousData: true,
  });

  const items = data?.results || [];
  const goto = (p) => { setPage(p); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return (
    <div className="px-4 md:px-12 py-8 pb-16">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Search results for</p>
      <div className="flex items-baseline justify-between flex-wrap gap-2 mt-1 mb-8">
        <h1 className="font-heading text-3xl md:text-4xl font-bold tracking-tight metallic-text">“{q}”</h1>
        {data && <span className="text-sm text-slate-500">{data.total_results} results · page {data.page} of {Math.min(data.total_pages, 500)}</span>}
      </div>
      {isLoading ? (
        <CardSkeleton />
      ) : items.length ? (
        <>
          <MediaGrid items={items} />
          <Pagination page={data.page} totalPages={data.total_pages} onChange={goto} />
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-24 text-slate-500" data-testid="search-empty">
          <SearchX size={48} className="mb-4 opacity-50" />
          <p className="text-lg font-medium">No results found</p>
          <p className="text-sm">Try a different title.</p>
        </div>
      )}
    </div>
  );
}
