import { useEffect, useState } from "react";
import { useWorld } from "../world/store";
import { ScreenView } from "./ScreenView";
import { HeadTag } from "./HeadTag";

const SCREEN_NAMES = { computer: "Ada's computer", simulator: "Patient simulator", microscope: "Microscope display" };
const MOOD_WORD: Record<string, string> = {
  neutral: "calm", focused: "focused", curious: "curious", happy: "happy", excited: "excited",
  puzzled: "puzzled", frustrated: "frustrated", tired: "sleepy",
};

function useNow() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function Header() {
  const r = useWorld((s) => s.researcher);
  const status = useWorld((s) => s.status);
  const mood = useWorld((s) => s.mood);
  const mode = useWorld((s) => s.mode);
  const follow = useWorld((s) => s.follow);
  const setFollow = useWorld((s) => s.setFollow);
  const now = useNow();
  return (
    <header className="hud">
      <div className="hud-title">
        <a className="hud-back" href="#/">← {r.name}'s website</a>
        <div className="hud-lab">The Living Lab</div>
        <div className="hud-sub">{r.name} · {r.title}</div>
      </div>
      <div className="hud-status">
        <span className="dot" /> {status} <span className="hud-mood">· feeling {MOOD_WORD[mood]}</span>
      </div>
      <div className="hud-right">
        <button className="cam-btn" onClick={() => setFollow(!follow)}>
          {follow ? "Whole lab" : `Follow ${r.name}`}
        </button>
        <span className={`badge ${mode}`}>{mode === "scripted" ? "Scripted demo" : mode === "replay" ? "Replay of real work" : "Live"}</span>
        <span className="hud-clock">{now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
      </div>
    </header>
  );
}

function ActivityLog() {
  const log = useWorld((s) => s.log);
  return (
    <aside className="log">
      <div className="panel-h">Lab notebook</div>
      <ul>
        {log.slice(-9).reverse().map((e, i) => (
          <li key={e.t + "-" + i} className={`log-${e.kind ?? "action"}`}>
            <span className="log-t">{new Date(e.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
            {e.text}
          </li>
        ))}
      </ul>
    </aside>
  );
}

function Inspector() {
  const inspected = useWorld((s) => s.inspected);
  const screens = useWorld((s) => s.screens);
  const library = useWorld((s) => s.library);
  const board = useWorld((s) => s.board);
  const r = useWorld((s) => s.researcher);
  const mood = useWorld((s) => s.mood);
  const thought = useWorld((s) => s.thought);
  const inspect = useWorld((s) => s.inspect);
  if (!inspected) return <div className="hint">Click the computer, the bookshelf, the whiteboard, the machines, or {r.name}</div>;
  let title = "";
  let body: React.ReactNode = null;
  if (inspected.kind === "screen") {
    title = SCREEN_NAMES[inspected.screen];
    body = <ScreenView c={screens[inspected.screen]} />;
  } else if (inspected.kind === "library") {
    title = `${r.name}'s library`;
    body = library.length ? (
      <ul className="lib">
        {library.map((b) => (
          <li key={b.id}><span className="spine" style={{ background: b.color }} />
            <div><div className="lib-t">{b.title}</div><div className="lib-s">{b.source}</div><div className="lib-n">{b.note}</div></div>
          </li>
        ))}
      </ul>
    ) : <p className="muted">No saved papers yet.</p>;
  } else if (inspected.kind === "board") {
    title = "Hypothesis board";
    body = board.length ? (
      <ul className="hyps">
        {board.map((h) => (
          <li key={h.id} className={`hyp hyp-${h.status}`}><b>{h.status}</b> {h.text}</li>
        ))}
      </ul>
    ) : <p className="muted">No hypotheses yet.</p>;
  } else if (inspected.kind === "researcher") {
    title = r.name;
    body = (
      <div className="prof">
        <p>{r.title}</p>
        <p>Feeling <b>{MOOD_WORD[mood]}</b>.</p>
        {thought && <p className="prof-thought">"{thought}"</p>}
        <p className="muted">In this demo she follows a script. In phase 2 an AI model decides what she does,
          within a hard daily budget.</p>
      </div>
    );
  }
  return (
    <aside className="inspector">
      <div className="panel-h">{title}<button onClick={() => inspect(null)} aria-label="Close">×</button></div>
      <div className="inspector-body">{body}</div>
    </aside>
  );
}

export function Overlay() {
  return (
    <>
      <HeadTag />
      <Header />
      <ActivityLog />
      <Inspector />
    </>
  );
}
