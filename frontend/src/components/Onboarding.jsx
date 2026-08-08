import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, ArrowRight, KeyRound } from "lucide-react";
import { api, BRAND } from "@/lib/api";

export default function Onboarding() {
  const qc = useQueryClient();
  const [torbox, setTorbox] = useState("");
  const [tmdb, setTmdb] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!torbox.trim() || !tmdb.trim()) return toast.error("Both keys are required to begin");
    setSaving(true);
    try {
      await api.updateSettings({ torbox_api_key: torbox.trim(), tmdb_api_key: tmdb.trim() });
      toast.success("You're all set!");
      qc.invalidateQueries();
    } catch {
      toast.error("Could not save keys");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#050507]/90 backdrop-blur-xl p-4" data-testid="onboarding-modal">
      <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-[#0C0D12] p-8 shadow-[0_20px_80px_rgba(0,0,0,0.6)] fade-up">
        <img src={BRAND.icon} alt="DMM" className="w-14 h-14 rounded-xl ring-1 ring-white/10 mb-5" />
        <h1 className="font-heading text-3xl font-extrabold tracking-tighter metallic-text">Welcome to DMM</h1>
        <p className="text-sm text-slate-400 mt-2">Bring your own keys — nothing is shared or stored anywhere but here. Two free keys get you running.</p>

        <div className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-200 flex items-center gap-2 mb-1.5"><KeyRound size={14} /> TorBox API Key</label>
            <input data-testid="onboarding-torbox" type="password" value={torbox} onChange={(e) => setTorbox(e.target.value)}
              placeholder="torbox.app → Settings → API"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-200 flex items-center gap-2 mb-1.5"><KeyRound size={14} /> TMDB API Key</label>
            <input data-testid="onboarding-tmdb" type="password" value={tmdb} onChange={(e) => setTmdb(e.target.value)}
              placeholder="themoviedb.org/settings/api (v3)"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
          </div>
        </div>

        <button data-testid="onboarding-submit" onClick={submit} disabled={saving}
          className="mt-6 w-full inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-6 py-3 text-sm font-bold text-white hover:brightness-110 transition-[filter] disabled:opacity-60">
          {saving ? <Loader2 size={16} className="animate-spin" /> : <>Start using DMM <ArrowRight size={16} /></>}
        </button>
      </div>
    </div>
  );
}
