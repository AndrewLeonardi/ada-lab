import type { ReactNode } from "react";

// A tiny, safe Markdown renderer for lab notes: headings, paragraphs, lists, block quotes,
// **bold**, *italic*, `code` and [links](url). No raw HTML is ever injected.

function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    const k = `${key}-${i++}`;
    if (t.startsWith("**")) out.push(<strong key={k}>{t.slice(2, -2)}</strong>);
    else if (t.startsWith("`")) out.push(<code key={k}>{t.slice(1, -1)}</code>);
    else if (t.startsWith("[")) {
      const [, label, url] = /\[([^\]]+)\]\(([^)]+)\)/.exec(t)!;
      const safe = /^(https?:|#|\/|mailto:)/.test(url) ? url : "#";
      out.push(<a key={k} href={safe} target={safe.startsWith("http") ? "_blank" : undefined} rel="noreferrer">{label}</a>);
    } else out.push(<em key={k}>{t.slice(1, -1)}</em>);
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text }: { text: string }) {
  const blocks = text.replace(/\r/g, "").split(/\n{2,}/);
  return (
    <div className="md">
      {blocks.map((b, i) => {
        const k = `b${i}`;
        const h = /^(#{1,4})\s+(.*)$/.exec(b);
        if (h) {
          const lvl = Math.min(4, h[1].length + 1);
          const Tag = (`h${lvl}`) as "h2" | "h3" | "h4";
          return <Tag key={k}>{inline(h[2], k)}</Tag>;
        }
        const lines = b.split("\n");
        if (lines.every((l) => /^\s*[-*]\s+/.test(l)))
          return <ul key={k}>{lines.map((l, j) => <li key={j}>{inline(l.replace(/^\s*[-*]\s+/, ""), `${k}${j}`)}</li>)}</ul>;
        if (lines.every((l) => /^\s*\d+\.\s+/.test(l)))
          return <ol key={k}>{lines.map((l, j) => <li key={j}>{inline(l.replace(/^\s*\d+\.\s+/, ""), `${k}${j}`)}</li>)}</ol>;
        if (lines.every((l) => l.startsWith(">")))
          return <blockquote key={k}>{inline(lines.map((l) => l.replace(/^>\s?/, "")).join(" "), k)}</blockquote>;
        return <p key={k}>{inline(lines.join(" "), k)}</p>;
      })}
    </div>
  );
}
