import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import SearchResults from "@/pages/SearchResults";
import Detail from "@/pages/Detail";
import Library from "@/pages/Library";
import Settings from "@/pages/Settings";
import Stremio from "@/pages/Stremio";

function App() {
  return (
    <div className="dark App grain">
      <BrowserRouter>
        <Toaster
          theme="dark"
          position="top-right"
          toastOptions={{
            style: {
              background: "#0C0D12",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "#F8FAFC",
            },
          }}
        />
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<SearchResults />} />
            <Route path="/browse/:type" element={<Home />} />
            <Route path="/title/:mediaType/:tmdbId" element={<Detail />} />
            <Route path="/library" element={<Library />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/stremio" element={<Stremio />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </div>
  );
}

export default App;
