import { Plus, Check } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export default function SaveTitle({id, type, title}) {
  const [saved, setSaved] = useState(null);
  const [busy, setBusy] = useState(false);
  const identity = type + "/" + id;
  async function save() {
    setBusy(true);
    try {
      await api.saveTitle({catalog_id:String(id), media_type:type, title});
      setSaved(identity);
      toast.success("Saved to DMM");
    } catch { toast.error("Could not save title"); }
    finally { setBusy(false); }
  }
  return <button aria-label={"Save " + title + " to DMM"} title={saved === identity ? "Saved in DMM" : "Save to DMM"} className="poster-plus" disabled={busy || saved === identity} onClick={save}>{saved === identity ? <Check size={16}/> : <Plus size={16}/>}</button>;
}
