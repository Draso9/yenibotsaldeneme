import type { ReactNode } from "react";

export function LegalMarkdown({ markdown }: Readonly<{ markdown: string }>) {
  const nodes: ReactNode[] = [];
  let listItems: { text: string; key: number }[] = [];

  const flushList = () => {
    if (!listItems.length) return;
    const items = listItems;
    listItems = [];
    nodes.push(<ul className="legal-public-list" key={`list-${items[0].key}`}>{items.map((item) => <li key={item.key}>{item.text}</li>)}</ul>);
  };

  markdown.split("\n").forEach((raw, index) => {
    const line = raw.trim();
    if (!line) {
      flushList();
      return;
    }
    if (line.startsWith("- ")) {
      listItems.push({ text: line.slice(2), key: index });
      return;
    }

    flushList();
    if (line.startsWith("### ")) nodes.push(<h3 key={index}>{line.slice(4)}</h3>);
    else if (line.startsWith("## ")) nodes.push(<h2 key={index}>{line.slice(3)}</h2>);
    else if (line.startsWith("# ")) nodes.push(<h1 key={index}>{line.slice(2)}</h1>);
    else nodes.push(<p key={index}>{line}</p>);
  });

  flushList();
  return <div className="legal-public-copy">{nodes}</div>;
}
