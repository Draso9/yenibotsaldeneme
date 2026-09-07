import type { ReactNode } from "react";

// The shared legal presenter emits headings, lists, paragraphs, bold and inline code.
// Build React text nodes so content never becomes executable HTML.
function inlineContent(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const tokens = /`([^`]+)`|\*\*([^*]+)\*\*/g;
  let offset = 0;
  for (const match of text.matchAll(tokens)) {
    nodes.push(text.slice(offset, match.index));
    nodes.push(match[1] !== undefined
      ? <code key={match.index}>{match[1]}</code>
      : <strong key={match.index}>{match[2]}</strong>);
    offset = match.index + match[0].length;
  }
  nodes.push(text.slice(offset));
  return nodes;
}

export function LegalMarkdown({ markdown }: Readonly<{ markdown: string }>) {
  const nodes: ReactNode[] = [];
  let listItems: { text: string; key: number }[] = [];
  let paragraph: string[] = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    nodes.push(<p key={`paragraph-${nodes.length}`}>{inlineContent(paragraph.join(" "))}</p>);
    paragraph = [];
  };

  const flushList = () => {
    if (!listItems.length) return;
    const items = listItems;
    listItems = [];
    nodes.push(<ul className="legal-public-list" key={`list-${items[0].key}`}>{items.map((item) => <li key={item.key}>{inlineContent(item.text)}</li>)}</ul>);
  };

  markdown.split("\n").forEach((raw, index) => {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      flushList();
      return;
    }
    if (line.startsWith("- ")) {
      flushParagraph();
      listItems.push({ text: line.slice(2), key: index });
      return;
    }

    flushList();
    if (/^#{1,3} /.test(line)) flushParagraph();
    if (line.startsWith("### ")) nodes.push(<h3 key={index}>{inlineContent(line.slice(4))}</h3>);
    else if (line.startsWith("## ")) nodes.push(<h2 key={index}>{inlineContent(line.slice(3))}</h2>);
    else if (line.startsWith("# ")) nodes.push(<h1 key={index}>{inlineContent(line.slice(2))}</h1>);
    else paragraph.push(line);
  });

  flushParagraph();
  flushList();
  return <div className="legal-public-copy">{nodes}</div>;
}
