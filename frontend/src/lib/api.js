import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const BRAND = {
  logo: "https://static.prod-images.emergentagent.com/jobs/4c3cfdd9-909a-42ca-a0a0-9a803d3f7427/images/c5b6008cf37951d9d0f85378fc1fddd0857a75b1f8aa1e8a04f82cd58bcfaac3.jpeg",
  icon: "https://static.prod-images.emergentagent.com/jobs/4c3cfdd9-909a-42ca-a0a0-9a803d3f7427/images/3432b210e7a4ebbaf55fd5f9cd44b4b5a753aa7f65c9c60b34bdfef7085e39aa.jpeg",
};

const client = axios.create({ baseURL: API });

export const transcodeUrl = (url, force = false) =>
  `${API}/stream/transcode?src=${encodeURIComponent(url)}${force ? "&force=1" : ""}`;

export const api = {
  config: () => client.get("/config").then((r) => r.data),
  updateSettings: (body) => client.post("/settings", body).then((r) => r.data),
  resetKeys: () => client.post("/reset").then((r) => r.data),
  warm: (type, id) => client.get(`/warm/${type}/${id}`).then((r) => r.data).catch(() => null),
  search: (q, page = 1) => client.get("/search", { params: { q, page } }).then((r) => r.data),
  trending: () => client.get("/trending").then((r) => r.data),
  discover: (type, page = 1) => client.get(`/discover/${type}`, { params: { page } }).then((r) => r.data),
  meta: (type, id) => client.get(`/meta/${type}/${id}`).then((r) => r.data),
  season: (id, s) => client.get(`/season/${id}/${s}`).then((r) => r.data),
  sources: (imdb, params) => client.get(`/sources/${imdb}`, { params }).then((r) => r.data),
  testKey: (service, key) => client.post("/test-key", { service, key }).then((r) => r.data),
  add: (body) => client.post("/torbox/add", body).then((r) => r.data),
  bulkAdd: (items) => client.post("/torbox/bulk-add", { items }).then((r) => r.data),
  cacheSeason: (body) => client.post("/torbox/cache-season", body).then((r) => r.data),
  resolve: (body) => client.post("/torbox/resolve", body).then((r) => r.data),
  library: () => client.get("/library").then((r) => r.data),
  deleteLib: (id) => client.delete(`/library/${id}`).then((r) => r.data),
  libraryDl: (tid, fid) => client.get(`/library/dl/${tid}/${fid}`).then((r) => r.data),
  manifestUrl: (body) => client.post("/stremio/manifest-url", body).then((r) => r.data),
};

export default api;
