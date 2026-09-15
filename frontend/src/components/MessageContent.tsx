type MessageContentProps = { content: string };

function renderText(text: string, key: string) {
  return <div className="message-markdown-text" key={key}>{text.split("\n").map((line, index) => <span key={`${key}-${index}`}>{line}{index < text.split("\n").length - 1 && <br />}</span>)}</div>;
}

export function MessageContent({ content }: MessageContentProps) {
  const blocks: JSX.Element[] = [];
  const pattern = /```([^\n]*)\n([\s\S]*?)```/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  let index = 0;
  while ((match = pattern.exec(content))) {
    if (match.index > cursor) blocks.push(renderText(content.slice(cursor, match.index), `text-${index}`));
    blocks.push(<pre className="message-code-block" key={`code-${index}`}><code data-language={match[1].trim() || undefined}>{match[2].replace(/\n$/, "")}</code></pre>);
    cursor = match.index + match[0].length;
    index += 1;
  }
  if (cursor < content.length || !blocks.length) blocks.push(renderText(content.slice(cursor), `text-${index}`));
  return <div className="message-markdown">{blocks}</div>;
}
