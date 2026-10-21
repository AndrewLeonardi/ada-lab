import { useEffect, useRef } from "react";
import { anchors } from "../world/anchors";
import { useWorld } from "../world/store";
import { EMOTE } from "../scene/Character";

/** Thought bubble, mood emote and name tag that follow the researcher's head on screen. */
export function HeadTag() {
  const ref = useRef<HTMLDivElement>(null);
  const thought = useWorld((s) => s.thought);
  const mood = useWorld((s) => s.mood);
  const activity = useWorld((s) => s.activity);
  const arrived = useWorld((s) => s.arrived);
  const station = useWorld((s) => s.station);
  const name = useWorld((s) => s.researcher.name);

  useEffect(() => {
    let id = 0;
    const tick = () => {
      const el = ref.current;
      if (el) {
        const a = anchors.head;
        el.style.transform = `translate3d(${a.x}px, ${a.y}px, 0) translate(-50%, -100%)`;
        el.style.visibility = a.visible ? "visible" : "hidden";
      }
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, []);

  const asleep = (activity === "sleep" || activity === "nap") && arrived === station;
  const music = activity === "listen_music" && arrived === station;
  const emote = EMOTE[mood];
  return (
    <div ref={ref} className="head-tag">
      <div className="above-head">
        {asleep ? (
          <div className="zzz"><span>z</span><span>z</span><span>Z</span></div>
        ) : music ? (
          <div className="zzz notes"><span>♪</span><span>♫</span><span>♪</span></div>
        ) : (
          <>
            {emote && <div className={`emote mood-${mood}`}>{emote}</div>}
            {thought && <div className="thought" key={thought}>{thought}</div>}
          </>
        )}
        <div className="nametag">{name}</div>
      </div>
    </div>
  );
}
