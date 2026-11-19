const groups = [
  ["Resolution", "resolutions", ["480p","720p","1080p","1440p","2160p"]],
  ["Presentation", "editions", ["IMAX","Open Matte"]],
  ["Source", "formats", ["REMUX","BluRay","WEB-DL","WEBRip","HDTV"]],
];
export function matchesRelease(quality, selected) {
  return groups.every(([,key]) => {
    const values = selected[key] || [];
    if (!values.length) return true;
    const actual = key === "resolutions" ? [quality.resolution] : key === "formats" ? [quality.source] : quality.editions || [];
    return values.some(value => actual.includes(value));
  });
}
export default function ReleaseFilters({value, onChange}) {
  return <details className="release-options"><summary>Release filters · {Object.values(value).flat().length || "Any"}</summary>
    {groups.map(([label,key,options])=><fieldset key={key}><legend>{label}</legend>{options.map(option=>{
      const selected=value[key] || [];
      return <label key={option}><input type="checkbox" checked={selected.includes(option)} onChange={e=>onChange({...value,[key]:e.target.checked?[...selected,option]:selected.filter(v=>v!==option)})}/> {option==="2160p"?"2160p / 4K":option}</label>;
    })}</fieldset>)}
    <button type="button" onClick={()=>onChange({})}>Clear release filters</button></details>;
}
