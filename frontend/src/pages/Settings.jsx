import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Key, CheckCircle2, XCircle, Save, Loader2, Server, Database } from "lucide-react";
import { api } from "@/lib/api";

export default function Settings() {
  const qc = useQueryClient();
  const { data: config, isLoading } = useQuery({ queryKey: ["config"], queryFn: api.config });
  const [key, setKey] = useState("");
  const [sources, setSources] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (config) setSources(config.sources || []);
  }, [config]);

  const toggleSource = (id) => {
    setSources((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));
  };

  const save = async () => {
    setSaving(true);
    try {
      const body = { sources };
      if (key.trim()) body.torbox_api_key = key.trim();
      await api.updateSettings(body);
      toast.success("Settings saved");
      setKey("");
      qc.invalidateQueries({ queryKey: ["config"] });
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const clearKey = async () => {
    setSaving(true);
    try {
      await api.updateSettings({ torbox_api_key: "" });
      toast.success("Reverted to default TorBox key");
      qc.invalidateQueries({ queryKey: ["config"] });
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <div className="p-12 flex justify-center"><Loader2 className="animate-spin text-blue-500" /></div>;

  return (
    <div className="px-4 md:px-12 py-8 pb-20 max-w-3xl">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Configuration</p>
      <h1 className="font-heading text-3xl md:text-4xl font-bold tracking-tight metallic-text mt-1 mb-8">Settings</h1>

      {/* Connection status */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 mb-6">
        <div className="flex items-center gap-3">
          {config?.torbox_connected ? <CheckCircle2 className="text-emerald-400" /> : <XCircle className="text-rose-400" />}
          <div>
            <div className="font-heading font-semibold text-white flex items-center gap-2"><Server size={16} /> TorBox Connection</div>
            <div className="text-sm text-slate-400" data-testid="settings-connection-status">
              {config?.torbox_connected
                ? `Connected as ${config.torbox_account?.email} · ${config.torbox_account?.premium ? "Premium" : "Free"} plan`
                : "Not connected"}
            </div>
          </div>
        </div>
      </div>

      {/* API key */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 mb-6">
        <label className="font-heading font-semibold text-white flex items-center gap-2 mb-1"><Key size={16} /> TorBox API Key</label>
        <p className="text-sm text-slate-500 mb-4">
          {config?.has_custom_key ? "Using your custom key." : "Using the built-in default key."} Paste your own key to override.
        </p>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            data-testid="settings-apikey-input"
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="Enter your TorBox API key…"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
          {config?.has_custom_key && (
            <button data-testid="settings-clearkey-btn" onClick={clearKey} className="rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/10 transition-colors">
              Use default
            </button>
          )}
        </div>
      </div>

      {/* Sources */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 mb-6">
        <div className="font-heading font-semibold text-white flex items-center gap-2 mb-1"><Database size={16} /> Indexer Sources</div>
        <p className="text-sm text-slate-500 mb-4">Choose where source results are pulled from.</p>
        <div className="space-y-2">
          {(config?.available_sources || []).map((s) => {
            const on = sources.includes(s.id);
            return (
              <button
                key={s.id}
                data-testid={`source-toggle-${s.id}`}
                onClick={() => toggleSource(s.id)}
                className={`w-full flex items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors ${
                  on ? "bg-blue-500/10 border-blue-500/30" : "bg-white/[0.02] border-white/10 hover:bg-white/5"
                }`}
              >
                <div>
                  <div className="text-sm font-medium text-slate-100">{s.name}</div>
                  <div className="text-[11px] text-slate-500">{s.types.join(", ")}</div>
                </div>
                <div className={`w-10 h-6 rounded-full p-0.5 transition-colors ${on ? "bg-blue-500" : "bg-white/10"}`}>
                  <div className={`w-5 h-5 rounded-full bg-white transition-transform ${on ? "translate-x-4" : ""}`} />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <button
        data-testid="settings-save-btn"
        onClick={save}
        disabled={saving}
        className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-6 py-3 text-sm font-bold text-white hover:brightness-110 transition-[filter] disabled:opacity-60"
      >
        {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save Settings
      </button>
    </div>
  );
}
