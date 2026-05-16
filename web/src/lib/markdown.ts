function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatInline(value: string): string {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

function renderList(lines: string[], ordered: boolean): string {
  const items = lines
    .map((line) =>
      ordered
        ? line.replace(/^\d+\.\s+/, "")
        : line.replace(/^[-*]\s+/, "")
    )
    .map((line) => `<li>${formatInline(line)}</li>`)
    .join("");
  return ordered ? `<ol>${items}</ol>` : `<ul>${items}</ul>`;
}

export function renderSimpleMarkdown(markdown: string): string {
  const normalized = markdown.replace(/\r\n/g, "\n").trim();
  if (!normalized) {
    return "<p>No content yet.</p>";
  }

  const blocks = normalized.split(/\n{2,}/);
  const html = blocks.map((block) => {
    const lines = block.split("\n").filter(Boolean);
    if (!lines.length) {
      return "";
    }

    if (lines.every((line) => /^[-*]\s+/.test(line))) {
      return renderList(lines, false);
    }

    if (lines.every((line) => /^\d+\.\s+/.test(line))) {
      return renderList(lines, true);
    }

    if (block.startsWith("```") && block.endsWith("```") && lines.length >= 2) {
      const code = lines.slice(1, -1).join("\n");
      return `<pre><code>${escapeHtml(code)}</code></pre>`;
    }

    const heading = lines[0].match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      const level = Math.min(heading[1].length, 3);
      const body = formatInline(heading[2]);
      const trailing = lines
        .slice(1)
        .map((line) => formatInline(line))
        .join("<br />");
      return trailing
        ? `<h${level}>${body}</h${level}><p>${trailing}</p>`
        : `<h${level}>${body}</h${level}>`;
    }

    return `<p>${lines.map((line) => formatInline(line)).join("<br />")}</p>`;
  });

  return html.join("");
}
