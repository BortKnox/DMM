import { useState } from "react";

export function usePosterSize() {
  const [size, setSize] = useState(() => {
    try { return localStorage.getItem("poster-size") || "150"; } catch { return "150"; }
  });
  function change(value) {
    setSize(value);
    try { localStorage.setItem("poster-size", value); } catch {}
  }
  return {control:<label>Poster size <select value={size} onChange={e => change(e.target.value)}>
    <option value="105">Small</option><option value="150">Medium</option><option value="210">Large</option>
  </select></label>, style:{display:"grid",gridTemplateColumns:`repeat(auto-fill,minmax(min(100%, ${size}px),1fr))`}};
}
