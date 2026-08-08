import { useEffect, useRef } from "react";
import { X, ExternalLink, Loader2, AlertTriangle } from "lucide-react";

export default function Player({ open, url, title, loading, onClose }) {
  const videoRef = useRef(null);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85 backdrop-blur-md p-4" data-testid="player-modal" onClick={onClose}>
      <div className="w-full max-w-5xl rounded-2xl border border-white/10 bg-[#0C0D12] overflow-hidden shadow-[0_20px_80px_rgba(0,0,0,0.7)]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <p className="text-sm font-medium text-slate-200 truncate pr-4">{title}</p>
          <button data-testid="player-close" onClick={onClose} className="rounded-full p-1.5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors"><X size={18} /></button>
        </div>
        <div className="aspect-video bg-black flex items-center justify-center">
          {loading ? (
            <div className="flex flex-col items-center gap-3 text-slate-400">
              <Loader2 className="animate-spin text-blue-500" size={36} />
              <p className="text-sm">Resolving stream from TorBox…</p>
            </div>
          ) : url ? (
            <video ref={videoRef} src={url} controls autoPlay className="w-full h-full" data-testid="player-video" />
          ) : null}
        </div>
        {url && !loading && (
          <div className="flex items-center justify-between gap-3 px-4 py-3 border-t border-white/10">
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <AlertTriangle size={12} /> MKV/HEVC may not play in-browser — use external if it stalls.
            </p>
            <a href={url} target="_blank" rel="noreferrer" data-testid="player-external"
              className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/10 transition-colors">
              <ExternalLink size={13} /> Open externally
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
