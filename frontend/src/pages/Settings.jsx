import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Key, CheckCircle2, XCircle, Save, Loader2, Server, Database, Zap } from "lucide-react";
import { api } from "@/lib/api";

const KEY_FIELDS = [
  { id: "torbox", field: "torbox_api_key", label: "TorBox API Key", required: true, testable: true, hint: "torbox.app → Settings → API. Powers caching, library & streaming." },
  { id: "tmdb", field: "tmdb_api_key", label: "TMDB API Key", required: true, testable: true, hint: "themoviedb.org/settings/api (v3). Posters, titles, catalogs." },
  { id: "omdb", field: "omdb_api_key", label: "OMDb API Key", required: false, testable: true, hint: "omdbapi.com. Rotten Tomatoes & Metacritic scores." },
  { id: "rpdb", field: "rpdb_api_key", label: "RPDB API Key", required: false, testable: true, hint: "ratingposterdb.com. Posters with ratings baked in." },
  { id: "fanart", field: "fanart_api_key", label: "Fanart.tv API Key", required: false, testable: true, hint: "fanart.tv. HD logos on title pages." },
  { id: "thetvdb", field: "thetvdb_api_key", label: "TheTVDB API Key", required: false, testable: true, hint: "thetvdb.com. Extended TV metadata." },
];

export default function Settings() {
  const qc = useQueryClient();
  const { data: config, isLoading } = useQuery({ queryKey: ["config"], queryFn: api.config });
  const [vals, setVals] = useState({});
  const [sources, setSources] = useState([]);
  const [saving, setSaving] = useState(false);
  const [tests, setTests] = useState({});

  useEffect(() => { if (config) setSources(config.sources || []); }, [config]);

  const toggleSource = (id) => setSources((p) => (p.includes(id) ? p.filter((s) => s !== id) : [...p, id]));

  const testKey = async (id, field) => {
    const key = vals[field]?.trim();
    if (!key) return toast.error("Enter a key first to test it");
    setTests((t) => ({ ...t, [id]: { loading: true } }));
    try {
      const res = await api.testKey(id, key);
      setTests((t) => ({ ...t, [id]: { ok: res.ok, msg: res.message } }));
      res.ok ? toast.success(res.message) : toast.error(res.message);
    } catch {
      setTests((t) => ({ ...t, [id]: { ok: false, msg: "Test failed" } }));
      toast.error("Test failed");
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      const body = { sources };
      let n = 0;
      KEY_FIELDS.forEach(({ field }) => { if (vals[field]?.trim()) { body[field] = vals[field].trim(); n++; } });
      await api.updateSettings(body);
      toast.success(n ? `Saved — ${n} key${n > 1 ? "s" : ""} updated & stored` : "Settings saved");
      setVals({});
      setTests({});
      qc.invalidateQueries();
    } catch { toast.error("Failed to save settings"); } finally { setSaving(false); }
  };

  if (isLoading) return <div className="p-12 flex justify-center"><Loader2 className="animate-spin text-blue-500" /></div>;
  const keysSet = config?.keys_set || {};

  return (
    <div className="px-4 md:px-12 py-8 pb-20 max-w-3xl">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Configuration</p>
      <h1 className="font-heading text-3xl md:text-4xl font-bold tracking-tight metallic-text mt-1 mb-8">Settings</h1>

      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 mb-6">
        <div className="flex items-center gap-3">
          {config?.torbox_connected ? <CheckCircle2 className="text-emerald-400" /> : <XCircle className="text-rose-400" />}
          <div>
            <div className="font-heading font-semibold text-white flex items-center gap-2"><Server size={16} /> TorBox Connection</div>
            <div className="text-sm text-slate-400" data-testid="settings-connection-status">
              {config?.torbox_connected ? `Connected as ${config.torbox_account?.email} · ${config.torbox_account?.premium ? "Premium" : "Free"}` : "Not connected — add your TorBox key below"}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 mb-6">
        <div className="font-heading font-semibold text-white flex items-center gap-2 mb-1"><Key size={16} /> API Keys</div>
        <p className="text-sm text-slate-500 mb-5">Keys are saved privately to this instance and remembered across sessions. Nothing is shipped or shared. Use <span className="text-blue-300">Test</span> to verify before saving.</p>
        <div className="space-y-4">
          {KEY_FIELDS.map(({ id, field, label, required, testable, hint }) => {
            const t = tests[id];
            return (
              <div key={id}>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-medium text-slate-200 flex items-center gap-2">
                    {label}{required && <span className="text-[10px] uppercase tracking-wider text-blue-400">Required</span>}
                  </label>
                  {keysSet[id] ? <span className="text-[11px] text-emerald-400 flex items-center gap-1"><CheckCircle2 size={11} /> Saved</span> : <span className="text-[11px] text-slate-500">Not set</span>}
                </div>
                <div className="flex gap-2">
                  <input data-testid={`settings-key-${id}`} type="password" value={vals[field] || ""}
                    onChange={(e) => { setVals((v) => ({ ...v, [field]: e.target.value })); setTests((x) => ({ ...x, [id]: undefined })); }}
                    placeholder={keysSet[id] ? "•••••••• saved (enter to replace)" : "Paste key…"}
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  {testable && (
                    <button data-testid={`settings-test-${id}`} onClick={() => testKey(id, field)} disabled={t?.loading}
                      className={`shrink-0 inline-flex items-center gap-1.5 rounded-lg border px-3 py-2.5 text-xs font-semibold transition-colors ${t?.ok === true ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : t?.ok === false ? "border-rose-500/40 bg-rose-500/10 text-rose-300" : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"}`}>
                      {t?.loading ? <Loader2 size={13} className="animate-spin" /> : t?.ok === true ? <CheckCircle2 size={13} /> : t?.ok === false ? <XCircle size={13} /> : <Zap size={13} />}
                      Test
                    </button>
                  )}
                </div>
                <p className={`text-[11px] mt-1 ${t?.msg ? (t.ok ? "text-emerald-400" : "text-rose-400") : "text-slate-500"}`}>{t?.msg || hint}</p>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 mb-6">
        <div className="font-heading font-semibold text-white flex items-center gap-2 mb-1"><Database size={16} /> Indexer Sources</div>
        <p className="text-sm text-slate-500 mb-4">Where source results are pulled from. Enable more to catch every cached release.</p>
        <div className="space-y-2">
          {(config?.available_sources || []).map((s) => {
            const on = sources.includes(s.id);
            return (
              <button key={s.id} data-testid={`source-toggle-${s.id}`} onClick={() => toggleSource(s.id)}
                className={`w-full flex items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors ${on ? "bg-blue-500/10 border-blue-500/30" : "bg-white/[0.02] border-white/10 hover:bg-white/5"}`}>
                <div><div className="text-sm font-medium text-slate-100">{s.name}</div><div className="text-[11px] text-slate-500">{s.desc} · {s.types.join(", ")}</div></div>
                <div className={`w-10 h-6 rounded-full p-0.5 transition-colors ${on ? "bg-blue-500" : "bg-white/10"}`}><div className={`w-5 h-5 rounded-full bg-white transition-transform ${on ? "translate-x-4" : ""}`} /></div>
              </button>
            );
          })}
        </div>
      </div>

      <button data-testid="settings-save-btn" onClick={save} disabled={saving}
        className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-6 py-3 text-sm font-bold text-white hover:brightness-110 transition-[filter] disabled:opacity-60">
        {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save Settings
      </button>
    </div>
  );
}
