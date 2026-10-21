import { useEffect } from "react";
import { Lab } from "./scene/Lab";
import { Overlay } from "./ui/Overlay";
import { startDirector } from "./world/director";
import { startReplay } from "./world/replay";
import { useWorld } from "./world/store";
import type { Activity, Mood, WorldEvent } from "./world/protocol";
import { useRoute } from "./site/router";
import { Layout } from "./site/Layout";
import { AboutPage, DataPage, Home, MethodsPage, NotePage, NotesPage, TrialPage } from "./site/Pages";
import { DATA } from "./site/data";

function LabView() {
  useEffect(() => {
    // Photo mode for checking expressions: #/lab?photo=<mood>&act=<activity>
    const q = new URLSearchParams(location.hash.split("?")[1] ?? location.search);
    const photo = q.get("photo") as Mood | null;
    if (photo) {
      const s = useWorld.getState();
      s.dispatch({ type: "goto", station: "center", activity: (q.get("act") as Activity) ?? "idle" });
      s.dispatch({ type: "mood", mood: photo });
      s.dispatch({ type: "status", text: `Photo mode: ${photo}` });
      useWorld.setState({ followZoom: Number(q.get("zoom") ?? 9) });
      s.setFollow(true);
      return;
    }
    let stop: (() => void) | null = null;
    let cancelled = false;
    // Replay her real work if any has been published; otherwise play the scripted demo day.
    fetch(DATA.events, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : []))
      .catch(() => [])
      .then((events: WorldEvent[]) => {
        if (cancelled) return;
        stop = events.length > 5 ? startReplay(events) : startDirector();
      });
    return () => { cancelled = true; stop?.(); };
  }, []);
  const clean = new URLSearchParams(location.hash.split("?")[1] ?? "").has("clean"); // for screenshots
  return (
    <div className="app">
      <Lab />
      {!clean && <Overlay />}
    </div>
  );
}

const startedInLab = (location.hash.replace(/^#\/?/, "").split("/")[0] ?? "").startsWith("lab");

export default function App() {
  const route = useRoute();
  const inLab = route[0]?.startsWith("lab") ?? false;
  // Moving between the 3D lab and the website is a full page load: tearing down a live WebGL
  // canvas mid-render is fragile, and a fresh load is instant from cache anyway.
  useEffect(() => {
    if (inLab !== startedInLab) location.reload();
  }, [inLab]);
  if (inLab) return startedInLab ? <LabView /> : null;
  let page;
  switch (route[0]) {
    case "data": page = <DataPage />; break;
    case "trial": page = <TrialPage pmid={route[1] ?? ""} />; break;
    case "notes": page = <NotesPage />; break;
    case "note": page = <NotePage slug={route[1] ?? ""} />; break;
    case "methods": page = <MethodsPage />; break;
    case "about": page = <AboutPage />; break;
    default: page = <Home />;
  }
  return <Layout route={route}>{page}</Layout>;
}
