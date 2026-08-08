import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { HardDrive, Play, Trash2, Loader2, RefreshCw, Zap, Clock, Library as LibIcon } from "lucide-react";
import { api } from "@/lib/api";

function StateBadge({ item }) {
  if (item.cached) return <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-300"><Zap size={10} /> Cached</span>;
  if ((item.progress || 0) < 100) return <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] font-semibold text-amber-300"><Clock size={10} /> {item.progress}%</span>;
  return <span className="rounded-md bg-white/5 border border-white/10 px-2 py-0.5 text-[10px] text-slate-400">{item.state}</span>;
}

function pickVideo(files = []) {
  const vids = files.filter((f) => /\.(mkv|mp4|avi|m4v|ts)$/i.test(f.name));
  const list = vids.length ? vids : files;
  return list.sort((a, b) => (b.size || 0) - (a.size || 0))[0];
}

export default function Library() {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(null);
  const { data, isLoading } = useQuery({ queryKey: ["library"], queryFn: api.library });

  const del = useMutation({
    mutationFn: (id) => api.deleteLib(id),
    onSuccess: () => {
      toast.success("Removed from library");
      qc.invalidateQueries({ queryKey: ["library"] });
    },
    onError: () => toast.error("Failed to remove"),
  });

  const play = async (item) => {
    const f = pickVideo(item.files);
    if (!f) return toast.error("No playable file");
    setBusy(item.id);
    try {
      const res = await api.libraryDl(item.id, f.id);
      window.open(res.url, "_blank");
      toast.success("Opening stream");
    } catch {
      toast.error("Could not get stream link");
    } finally {
      setBusy(null);
    }
  };

  const lib = data?.library || [];

  return (
    <div className="px-4 md:px-12 py-8 pb-20">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">TorBox</p>
          <h1 className="font-heading text-3xl md:text-4xl font-bold tracking-tight metallic-text mt-1 flex items-center gap-3">
            <LibIcon /> Your Library
          </h1>
        </div>
        <button
          data-testid="library-refresh-btn"
          onClick={() => qc.invalidateQueries({ queryKey: ["library"] })}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 hover:bg-white/10 transition-colors"
        >
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="grid gap-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-24 rounded-xl skeleton" />)}
        </div>
      ) : lib.length ? (
        <div className="grid gap-3" data-testid="library-list">
          {lib.map((item) => (
            <div key={item.id} className="flex flex-col md:flex-row md:items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3 hover:bg-white/[0.04] transition-colors">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <StateBadge item={item} />
                  <span className="text-[11px] text-slate-500 inline-flex items-center gap-1"><HardDrive size={11} /> {item.size_h}</span>
                  <span className="text-[11px] text-slate-500">{item.files?.length || 0} file(s)</span>
                </div>
                <p className="text-sm text-slate-200 truncate font-medium" title={item.name}>{item.name}</p>
                {(item.progress || 0) < 100 && (
                  <div className="mt-2 h-1 w-full max-w-sm rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-blue-500 to-blue-300" style={{ width: `${item.progress}%` }} />
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  data-testid={`library-play-${item.id}`}
                  onClick={() => play(item)}
                  disabled={busy === item.id || !item.download_present}
                  className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-4 py-2 text-xs font-semibold text-white hover:brightness-110 transition-[filter] disabled:opacity-50"
                >
                  {busy === item.id ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} className="fill-white" />} Play
                </button>
                <button
                  data-testid={`library-delete-${item.id}`}
                  onClick={() => del.mutate(item.id)}
                  className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 p-2 text-slate-400 hover:text-rose-400 hover:border-rose-500/30 transition-colors"
                  title="Remove"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="py-24 text-center text-slate-500" data-testid="library-empty">
          <LibIcon size={44} className="mx-auto mb-4 opacity-40" />
          <p className="text-lg font-medium">Your library is empty</p>
          <p className="text-sm">Search for something and add it to TorBox.</p>
        </div>
      )}
    </div>
  );
}
