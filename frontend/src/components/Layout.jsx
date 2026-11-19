import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Search, Home, Library, Settings, Puzzle, Clapperboard, Tv, Sparkles, Zap } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";


const navItems = [
  { to: "/", label: "Discover", icon: Home },
  { to: "/browse/movie", label: "Movies", icon: Clapperboard },
  { to: "/browse/series", label: "TV Shows", icon: Tv },
  { to: "/library", label: "Library", icon: Library },
  { to: "/stremio", label: "Add Plugin", icon: Puzzle },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout({ children }) {
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem("discover-theme") === "dark"; }
    catch { return false; }
  });
  function toggleTheme() {
    setDark(!dark);
    try { localStorage.setItem("discover-theme", dark ? "light" : "dark"); }
    catch { /* The choice still applies for this visit. */ }
  }
  const navigate = useNavigate();
  const location = useLocation();
  const [q, setQ] = useState("");

  const { data: config } = useQuery({ queryKey: ["config"], queryFn: api.config });

  useEffect(() => {
    if (location.pathname !== "/search") setQ("");
  }, [location.pathname]);

  const submit = (e) => {
    e.preventDefault();
    if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`);
  };

  return (
    <div data-theme={dark ? "dark" : "light"} className="bench min-h-screen flex bg-[#050507] text-slate-100 relative z-[2]">

      {/* Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 shrink-0 border-r border-white/5 bg-[#08090d] sticky top-0 h-screen">
        <Link to="/" data-testid="sidebar-logo" className="flex items-center gap-3 px-6 py-6">
          <span className="bench-mark" aria-label="DMM">DM</span>
          <div className="leading-tight">
            <div className="font-heading font-extrabold text-lg metallic-text tracking-tight">DMM</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Debrid Media Manager</div>
          </div>
        </Link>

        <nav className="flex-1 px-3 space-y-1 mt-2">
          {navItems.map(({ to, label, icon: Icon }) => {
            const active = to === "/" ? location.pathname === "/" : location.pathname.startsWith(to);
            return (
              <Link
                key={to}
                to={to}
                data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200 ${
                  active
                    ? "bg-blue-500/10 text-blue-300 border border-blue-500/20"
                    : "text-slate-400 hover:text-slate-100 hover:bg-white/5 border border-transparent"
                }`}
              >
                <Icon size={18} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4">
          <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <Zap size={14} className={config?.torbox_connected ? "text-emerald-400" : "text-slate-500"} />
              TorBox
            </div>
            <div className="mt-1 text-[11px] text-slate-500 truncate" data-testid="torbox-status">
              {config?.torbox_connected
                ? config?.torbox_account?.email || "Connected"
                : "Not connected"}
            </div>
          </div>
          <div className="mt-3 text-center text-[10px] text-slate-600">Debrid Media Manager · by Bort Knox</div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <header className="sticky top-0 z-30 bg-[#0C0D12]/70 backdrop-blur-xl border-b border-white/10">
          <div className="flex items-center gap-4 px-4 md:px-8 py-3.5">
            <Link to="/" className="lg:hidden flex items-center gap-2">
              <span className="bench-mark" aria-label="DMM">DM</span>
            </Link>
            <form onSubmit={submit} className="flex-1 max-w-2xl">
              <div className="relative group">
                <Search size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                <input
                  data-testid="global-search-input"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search movies & shows…"
                  className="w-full bg-white/5 border border-white/10 rounded-full pl-11 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500/40 transition-shadow"
                />
              </div>
            </form>
      <button className="bench-theme" aria-pressed={dark} onClick={toggleTheme}>Dark mode</button>
            <Link
              to="/stremio"
              data-testid="header-stremio-btn"
              className="hidden sm:inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-blue-400 px-4 py-2 text-sm font-semibold text-white hover:brightness-110 transition-[filter] shadow-[0_4px_20px_rgba(59,130,246,0.35)]"
            >
              <Sparkles size={15} /> Add Plugin
            </Link>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        {/* Mobile nav */}
        <nav className="lg:hidden sticky bottom-0 z-30 bg-[#0C0D12]/90 backdrop-blur-xl border-t border-white/10 flex justify-around gap-1 overflow-x-auto py-2">
          {navItems.map(({ to, label, icon: Icon }) => {
            const active = to === "/" ? location.pathname === "/" : location.pathname.startsWith(to);
            return (
              <Link key={to} to={to} className={`flex flex-col items-center gap-0.5 px-2 py-1 text-[10px] ${active ? "text-blue-400" : "text-slate-500"}`}>
                <Icon size={19} />
                {label.split(" ")[0]}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
