const el = id => document.getElementById(id);
let items = [], page = 0, sequence = 0;
const dialog = el("detail");
dialog.querySelector("button").onclick = () => dialog.close();
function render() {
  const count = Number(el("size").value);
  const start = page * count;
  el("grid").replaceChildren();
  for (const item of items.slice(start, start + count)) {
    const button = document.createElement("button");
    const image = document.createElement("img");
    image.alt = ""; image.loading = "lazy"; image.src = item.poster;
    const title = document.createElement("strong");
    title.textContent = item.name;
    button.append(image, title);
    button.onclick = () => {
      dialog.querySelector("h2").textContent = item.name;
      dialog.querySelector("p").textContent = [item.releaseInfo, item.description].filter(Boolean).join(" · ");
      dialog.showModal();
    };
    el("grid").append(button);
  }
  el("prev").disabled = page === 0;
  el("next").disabled = start + count >= items.length;
  el("status").textContent = items.length ? (start+1)+"–"+Math.min(start+count,items.length)+" of "+items.length : "No titles found.";
}
async function load() {
  const current = ++sequence;
  items = []; page = 0; render(); el("status").textContent = "Loading catalogue…";
  const q = el("query").value.trim();
  const url = "https://v3-cinemeta.strem.io/catalog/"+el("kind").value+"/top"+(q?"/search="+encodeURIComponent(q):"")+".json";
  try {
    const response = await fetch(url);
    if (!response.ok) throw Error();
    const data = await response.json();
    if (current !== sequence) return;
    items = data.metas || []; render();
  } catch { if(current===sequence) el("status").textContent="Catalogue unavailable. Press Search to retry."; }
}
el("form").onsubmit=e=>{e.preventDefault();load()};
el("kind").onchange=load;
el("size").onchange=()=>{page=0;render()};
el("prev").onclick=()=>{page--;render()};
el("next").onclick=()=>{page++;render()};
load();
