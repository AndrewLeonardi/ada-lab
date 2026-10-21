import type { ScreenContent } from "../world/protocol";

/** Crisp, readable HTML version of whatever a screen in the lab shows. */
export function ScreenView({ c }: { c: ScreenContent }) {
  switch (c.app) {
    case "idle":
      return <div className="sv-idle">{c.title ?? "Idle"}</div>;
    case "search":
      return (
        <div className="sv">
          <div className="sv-url">{c.url}</div>
          <div className="sv-query">{c.query}</div>
          <ol className="sv-results">
            {c.results.map((r, i) => (
              <li key={i}><div className="sv-rt">{r.title}</div><div className="sv-rm">{r.meta}</div></li>
            ))}
          </ol>
        </div>
      );
    case "paper":
      return (
        <div className="sv">
          <div className="sv-url">{c.url}</div>
          <h3 className="sv-title">{c.title}</h3>
          <div className="sv-rm">{c.authors} · {c.journal}</div>
          <div className="sv-body">{c.body.split("\n").map((p, i) => <p key={i}>{p}</p>)}</div>
        </div>
      );
    case "notebook":
      return (
        <div className="sv">
          <div className="sv-url">{c.title}</div>
          {c.cells.map((cell, i) => (
            <pre key={i} className={`sv-cell sv-${cell.kind}`}>{cell.text}</pre>
          ))}
        </div>
      );
    case "trial":
      return (
        <div className="sv">
          <h3 className="sv-title">{c.title}</h3>
          <div className="sv-rm">{c.status}</div>
          <svg viewBox="0 0 320 180" className="sv-km">
            <line x1="30" y1="10" x2="30" y2="160" stroke="#6b8790" />
            <line x1="30" y1="160" x2="310" y2="160" stroke="#6b8790" />
            {(c.arms ?? []).map((a) => {
              const maxM = Math.max(...a.curve.map((p) => p[0]));
              let d = "";
              let prev = 10;
              a.curve.forEach(([m, s], i) => {
                const x = 30 + (m / maxM) * 280;
                const y = 160 - s * 150;
                d += i === 0 ? `M${x},${y}` : ` L${x},${prev} L${x},${y}`;
                prev = y;
              });
              return <path key={a.name} d={d} fill="none" stroke={a.color} strokeWidth={2.5} />;
            })}
          </svg>
          <ul className="sv-legend">
            {(c.arms ?? []).map((a) => (
              <li key={a.name}><span style={{ background: a.color }} />{a.name}{a.median ? ` (median ${a.median})` : ""}</li>
            ))}
          </ul>
        </div>
      );
    case "tissue":
      return (
        <div className="sv">
          <h3 className="sv-title">{c.title}</h3>
          <img src={c.image} alt={c.caption} className="sv-img" />
          <div className="sv-rm">{c.caption}</div>
        </div>
      );
  }
}
