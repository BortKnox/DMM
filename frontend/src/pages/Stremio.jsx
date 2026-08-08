import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Puzzle, Copy, ExternalLink, Loader2, Zap, Sparkles, Terminal, CheckCircle2 } from "lucide-react";
import { api, BRAND } from "@/lib/api";

const STEPS = [
  "Pick the indexer sources you want the addon to search.",
  "Generate your personal manifest — it embeds your TorBox key securely.",
  "Click Install to Stremio, or copy the URL into Stremio › Addons › paste.",
];

export default function Stremio() {
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: api.config });
  const [sources, setSources] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const active = sources ?? config?.sources ?? [];

  const toggle = (id) => {
    const base = sources ?? config?.sources ?? [];
    setSources(base.includes(id) ? base.filter((s) => s !== id) : [...base, id]);
    setResult(null);
  };

  const generate = async () => {
    setLoading(true);
    try {
      const res = await api.manifestUrl({ sources: active });
      setResult(res);
      toast.success("Manifest generated");
    } catch {
      toast.error("Failed to generate manifest");
    } finally {
      setLoading(false);
    }
  };

  const copy = () => {
    navigator.clipboard.writeText(result.manifest_url);
    setCopied(true);
    toast.success("Manifest URL copied");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="px-4 md:px-12 py-8 pb-20 max-w-4xl">
      <div className="flex items-center gap-4 mb-8">
        <img src={BRAND.icon} alt="DMM" className="w-14 h-14 rounded-xl ring-1 ring-white/10" />
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">One click integration</p>
          <h1 className="font-heading text-3xl md:text-4xl font-bold tracking-tight metallic-text mt-1 flex items-center gap-2">
            <Puzzle /> Stremio Addon
          </h1>
        </div>
      </div>

      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 mb-6">
        <p className="text-sm text-slate-300 leading-relaxed">
          Turn DMM into a native Stremio addon. It surfaces <span className="text-emerald-400 font-semibold">cached TorBox streams</span> instantly,
          adds uncached items on demand, and lists your TorBox library as a browsable catalog inside Stremio.
        </p>
        <div className="mt-5 grid gap-3">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="w-6 h-6 shrink-0 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-bold flex items-center justify-center">{i + 1}</div>
              <p className="text-sm text-slate-400 pt-0.5">{s}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Sources */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 mb-6">
        <div className="font-heading font-semibold text-white mb-4 flex items-center gap-2"><Sparkles size={16} /> Included Sources</div>
        <div className="flex flex-wrap gap-2">
          {(config?.available_sources || []).map((s) => {
            const on = active.includes(s.id);
            return (
              <button
                key={s.id}
                data-testid={`stremio-source-${s.id}`}
                onClick={() => toggle(s.id)}
                className={`rounded-full border px-4 py-2 text-sm font-medium transition-colors ${
                  on ? "bg-blue-500/15 border-blue-500/40 text-blue-300" : "bg-white/5 border-white/10 text-slate-400 hover:text-slate-200"
                }`}
              >
                {on && <CheckCircle2 size={13} className="inline mr-1.5 -mt-0.5" />}
                {s.name}
              </button>
            );
          })}
        </div>
        <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
          <Zap size={13} className={config?.torbox_connected ? "text-emerald-400" : "text-slate-500"} />
          {config?.has_custom_key ? "Your custom TorBox key will be embedded." : "The built-in TorBox key will be embedded."}
        </div>
      </div>

      <button
        data-testid="stremio-generate-btn"
        onClick={generate}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-6 py-3 text-sm font-bold text-white hover:brightness-110 transition-[filter] disabled:opacity-60"
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} Generate Manifest
      </button>

      {/* Result */}
      {result && (
        <div className="mt-6 rounded-2xl border border-blue-500/20 bg-blue-500/[0.03] p-6 fade-up" data-testid="stremio-result">
          <div className="font-heading font-semibold text-white mb-1 flex items-center gap-2"><Terminal size={16} /> Your Manifest</div>
          <p className="text-xs text-slate-500 mb-4">Install with one click, or copy the URL manually into Stremio.</p>

          <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/40 px-3 py-2.5 mb-4">
            <code className="flex-1 text-xs text-slate-300 truncate font-mono" data-testid="stremio-manifest-url">{result.manifest_url}</code>
            <button data-testid="stremio-copy-btn" onClick={copy} className="shrink-0 rounded-md border border-white/10 bg-white/5 p-1.5 text-slate-400 hover:text-slate-100 transition-colors">
              {copied ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}
            </button>
          </div>

          <div className="flex flex-wrap gap-3">
            <a
              data-testid="stremio-install-btn"
              href={result.install_url}
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-6 py-3 text-sm font-bold text-white hover:brightness-110 transition-[filter] shadow-[0_6px_24px_rgba(59,130,246,0.4)]"
            >
              <Puzzle size={16} /> Install to Stremio
            </a>
            <a
              href={`https://web.stremio.com/#/addons?addon=${encodeURIComponent(result.manifest_url)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-slate-100 hover:bg-white/10 transition-colors"
            >
              <ExternalLink size={15} /> Open Stremio Web
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
