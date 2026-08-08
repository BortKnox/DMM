import { useState } from "react";
import { Zap, Download, Copy, Play, HardDrive, Users, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

function Badge({ children, tone = "default" }) {
  const tones = {
    default: "bg-white/5 border-white/10 text-slate-300",
    cached: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
    res: "bg-blue-500/10 border-blue-500/30 text-blue-200",
    hdr: "bg-amber-500/10 border-amber-500/30 text-amber-300",
  };
  return (
    <span className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-semibold ${tones[tone]}`}>
      {children}
    </span>
  );
}

export default function SourceRow({ source, mediaContext }) {
  const [busy, setBusy] = useState(null);
  const [added, setAdded] = useState(false);
  const q = source.quality || {};

  const doResolve = async () => {
    setBusy("play");
    try {
      const res = await api.resolve({
        hash: source.hash,
        name: source.name,
        season: mediaContext?.season ?? null,
        episode: mediaContext?.episode ?? null,
      });
      window.open(res.url, "_blank");
      toast.success("Stream ready — opening player");
    } catch (e) {
      toast.error("Could not resolve stream");
    } finally {
      setBusy(null);
    }
  };

  const doAdd = async () => {
    setBusy("add");
    try {
      const res = await api.add({ hash: source.hash, name: source.name });
      if (res.success) {
        setAdded(true);
        toast.success(res.detail || "Added to TorBox");
      } else {
        toast.error(res.detail || "Failed to add");
      }
    } catch (e) {
      toast.error("Failed to add to TorBox");
    } finally {
      setBusy(null);
    }
  };

  const copyMagnet = () => {
    navigator.clipboard.writeText(source.magnet);
    toast.success("Magnet copied");
  };

  return (
    <div
      data-testid={`source-row-${source.hash.slice(0, 8)}`}
      className={`flex flex-col md:flex-row md:items-center gap-3 rounded-lg border px-4 py-3 transition-colors duration-200 hover:bg-white/[0.03] ${
        source.cached ? "border-emerald-500/20 bg-emerald-500/[0.03]" : "border-white/5 bg-white/[0.01]"
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
          {source.cached && (
            <Badge tone="cached">
              <Zap size={10} className="mr-0.5 fill-emerald-300" /> Cached
            </Badge>
          )}
          {q.resolution && <Badge tone="res">{q.resolution}</Badge>}
          {q.source && <Badge>{q.source}</Badge>}
          {q.codec && <Badge>{q.codec}</Badge>}
          {(q.hdr || []).map((h) => (
            <Badge key={h} tone="hdr">{h}</Badge>
          ))}
          {q.audio && <Badge>{q.audio}</Badge>}
        </div>
        <p className="text-sm text-slate-200 truncate font-medium" title={source.name}>
          {source.name}
        </p>
        <div className="flex items-center gap-4 mt-1 text-[11px] text-slate-500">
          <span className="inline-flex items-center gap-1"><HardDrive size={11} /> {source.size_h}</span>
          <span className="inline-flex items-center gap-1"><Users size={11} /> {source.seeders} seeders</span>
          <span className="uppercase tracking-wider">{source.tracker}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          data-testid={`play-btn-${source.hash.slice(0, 8)}`}
          onClick={doResolve}
          disabled={busy === "play"}
          className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-3.5 py-2 text-xs font-semibold text-white hover:brightness-110 transition-[filter] disabled:opacity-60"
        >
          {busy === "play" ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} className="fill-white" />}
          {source.cached ? "Play" : "Cache & Play"}
        </button>
        <button
          data-testid={`add-btn-${source.hash.slice(0, 8)}`}
          onClick={doAdd}
          disabled={busy === "add" || added}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-white/10 transition-colors disabled:opacity-60"
        >
          {added ? <CheckCircle2 size={13} className="text-emerald-400" /> : busy === "add" ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
          {added ? "Added" : "Add"}
        </button>
        <button
          data-testid={`copy-btn-${source.hash.slice(0, 8)}`}
          onClick={copyMagnet}
          className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 p-2 text-slate-400 hover:text-slate-100 hover:bg-white/10 transition-colors"
          title="Copy magnet"
        >
          <Copy size={13} />
        </button>
      </div>
    </div>
  );
}
