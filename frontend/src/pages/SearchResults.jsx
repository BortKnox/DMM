import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { SearchX } from "lucide-react";
import { api } from "@/lib/api";
import { MediaGrid, CardSkeleton } from "@/components/MediaCard";

export default function SearchResults() {
  const [params] = useSearchParams();
  const q = params.get("q") || "";

  const { data, isLoading } = useQuery({
    queryKey: ["search", q],
    queryFn: () => api.search(q),
    enabled: !!q,
  });

  const items = data?.results || [];

  return (
    <div className="px-4 md:px-12 py-8 pb-16">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Search results for</p>
      <h1 className="font-heading text-3xl md:text-4xl font-bold tracking-tight metallic-text mt-1 mb-8">
        “{q}”
      </h1>
      {isLoading ? (
        <CardSkeleton />
      ) : items.length ? (
        <MediaGrid items={items} />
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
