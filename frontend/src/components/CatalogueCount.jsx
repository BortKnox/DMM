import { useState } from "react";

export function useCatalogueCount() {
  const [count, setCount] = useState(20);
  return {count, control:<label>Titles per page <select value={count} onChange={event=>setCount(Number(event.target.value))}>{[20,40,80].map(n=><option key={n}>{n}</option>)}</select></label>};
}

// Providers return up to 20 titles per page. Only request the extra pages a reader selects.
export async function cataloguePage(fetchPage, page, count) {
  const group = count / 20;
  const start = (page - 1) * group + 1;
  const first = await fetchPage(start);
  const remaining = Math.max(0, Math.min(group - 1, first.total_pages - start));
  const rest = await Promise.all(Array.from({length:remaining}, (_, i)=>fetchPage(start + i + 1)));
  const unique = new Map();
  for (const part of [first,...rest]) for (const item of part.results) unique.set(item.media_type + ":" + item.id,item);
  return {...first, results:[...unique.values()], page, total_pages:Math.ceil(first.total_pages/group)};
}
