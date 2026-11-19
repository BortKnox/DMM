import { useState } from "react";
import { Link } from "react-router-dom";
import "./Discover.css";

// Editorial connections are deliberately small enough to inspect and tune.
const films = [
  [968, "tt0072890", "Dog Day Afternoon", 1975, 125, "A Brooklyn bank robbery turns into a street spectacle. The crowd outside becomes as important as the hostages inside.", ["Under pressure", "City streets", "True stories"]],
  [26405, "tt0067541", "Wake in Fright", 1971, 109, "A schoolteacher misses his way home in an outback mining town where every friendly offer comes with a cost.", ["Under pressure", "Small towns"]],
  [19913, "tt1022603", "(500) Days of Summer", 2009, 95, "A relationship remembered out of order, with Los Angeles playing witness to every hopeful misreading.", ["Lighter touch", "City streets", "Odd couples"]],
  [275, "tt0116282", "Fargo", 1996, 98, "A staged kidnapping unravels in the Minnesota snow. One remarkably patient detective picks up the thread.", ["Small towns", "Under pressure", "Dry humour"]],
  [13852, "tt0118826", "The Castle", 1997, 85, "A Melbourne family takes its fight for a beloved, airport-adjacent home all the way to court.", ["Underdogs", "Lighter touch", "Dry humour"]],
  [164, "tt0054698", "Breakfast at Tiffany’s", 1961, 115, "Two neighbours in Manhattan discover how much of their carefully assembled lives is an act.", ["City streets", "Odd couples", "Lighter touch"]],
  [9675, "tt0375063", "Sideways", 2004, 127, "Two old friends set out through wine country before a wedding, carrying much more baggage than either admits.", ["Odd couples", "Small towns", "Dry humour"]],
  [916, "tt0062765", "Bullitt", 1968, 114, "A witness protection detail sends a San Francisco detective into a pursuit through the city's steep streets.", ["City streets", "Under pressure"]],
  [4638, "tt0425112", "Hot Fuzz", 2007, 121, "A London cop lands in an English village where the paperwork is quiet and the accidents are suspiciously frequent.", ["Small towns", "Odd couples", "Dry humour"]],
  [39356, "tt1560139", "Boy", 2010, 88, "On the East Coast of New Zealand, a Michael Jackson fan finally gets to spend time with the dad he has spent years imagining.", ["Underdogs", "Small towns", "Lighter touch"]],
].map(([id, imdb, title, year, minutes, pitch, tags]) => ({id, imdb, title, year, minutes, pitch, tags}));

const moods = ["Everything", "Under pressure", "Lighter touch", "Underdogs", "Small towns", "Dry humour"];
const art = (film, type) => `https://images.metahub.space/${type}/${type === "poster" ? "small" : "medium"}/${film.imdb}/img`;
const overlap = (a, b) => a.tags.filter(tag => b.tags.includes(tag));

export default function Discover() {
  const [current, setCurrent] = useState(films[0]);
  const [mood, setMood] = useState("Everything");
  const [history, setHistory] = useState([]);
  const [origin, setOrigin] = useState(null);
  const connected = films.filter(f => f !== current && (mood === "Everything" || f.tags.includes(mood)))
    .sort((a, b) => overlap(current, b).length - overlap(current, a).length);
  function choose(next) {
    setHistory([...history, {current, mood, origin}]);
    setOrigin(current);
    setCurrent(next);
  }
  function back() {
    const prior = history[history.length - 1];
    setCurrent(prior.current);
    setOrigin(prior.origin);
    setMood(prior.mood);
    setHistory(history.slice(0, -1));
  }
  return <div className="discovery">
    <header><span className="desk-label">BORT / SCREENING ROOM</span><h1>Discover</h1>

    </header>
    <section className="screen" aria-label="Featured pick">
      <img className="still" src={art(current,"background")} alt="" key={current.id}/>
      <div className="feature" aria-live="polite"><small>{current.year}　/　{current.minutes} MIN</small>
        <h2>{current.title}</h2><p>{current.pitch}</p>
        <div className="actions"><Link to={`/title/movie/${current.imdb}`}>Find a release</Link>{history.length > 0 && <button onClick={back}>Previous pick</button>}</div>
      </div>
    </section>
    <section className="shelf"><div className="section-head"><h2>Where to next?</h2><small>TONIGHT’S SELECTION</small></div>
      <div className="moods" aria-label="Filter suggestions">{moods.map(m => <button key={m} aria-pressed={mood === m} onClick={() => setMood(m)}>{m}</button>)}</div>
      <div className="picks">{connected.map(f => <button className="pick" key={f.id} onClick={() => {choose(f); window.scrollTo({top:0,behavior:"instant"});}}>
        <img src={art(f,"poster")} alt="" loading="lazy"/><span><small>{f.year} · {f.minutes} min</small><strong>{f.title}</strong><em>{overlap(current,f)[0] || (mood === "Everything" ? f.tags[0] : mood)}</em></span>
      </button>)}</div>
      {origin && <p className="trail">Last pick · {origin.title}</p>}
    </section>
  </div>;
}
