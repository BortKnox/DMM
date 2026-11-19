import { useEffect, useRef, useState } from "react";
import { X, ExternalLink, Loader2, Wand2, Zap } from "lucide-react";
import { transcodeUrl } from "@/lib/api";

export default function Player({ open, url, title, loading, onClose }) {
  const videoRef = useRef(null);
  const [failure, setFailure] = useState("");
  const [universal, setUniversal] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => { setUniversal(false); setFailure(""); }, [url, open]);

  if (!open) return null;

  const src = url ? (universal ? transcodeUrl(url) : url) : null;

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
              <p className="text-sm">Resolving stream from TorBoxâ€¦</p>
            </div>
          ) : src ? (
            <video ref={videoRef} key={src} src={src} onError={(event) => {
              const code = event.currentTarget.error?.code;
              setFailure(code === 2 ? "The network stream was interrupted." : code === 3 ? "The browser could not decode this stream." : "The browser could not open this stream.");
            }} controls playsInline preload="auto" className="w-full h-full" data-testid="player-video">
              Your browser canâ€™t play this stream.
            </video>
          ) : null}
        </div>
        {failure && <p role="alert" className="px-4 py-2">{failure} {universal ? "Try opening the original externally." : "Try server conversion below."}</p>}
        {url && !loading && (
          <div className="flex items-center justify-between gap-3 px-4 py-3 border-t border-white/10 flex-wrap">
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              {universal
                ? <><Wand2 size={12} className="text-blue-400" /> Converting for this browser · stereo AAC. Skip ahead is unavailable until that section is converted.</>
                : <><Zap size={12} className="text-amber-400" /> Direct playback. Picture but no sound? Try server conversion.</>}
            </p>
            <div className="flex items-center gap-2">
              <button data-testid="player-universal" onClick={() => { setFailure(""); setUniversal((v) => !v); }}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${universal ? "border-blue-500/50 bg-blue-500/15 text-blue-200" : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"}`}>
                <Wand2 size={13} /> {universal ? "Use direct playback" : "Use server conversion"}
              </button>
              <a href={url} target="_blank" rel="noreferrer" data-testid="player-external"
                className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/10 transition-colors">
                <ExternalLink size={13} /> Open externally
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
