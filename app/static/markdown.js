/*
 * A small, dependency-free Markdown renderer for chat answers.
 * Everything is HTML-escaped first, so model output can never inject markup.
 * Supports: headings, paragraphs, bold/italic, inline code, fenced code,
 * bullet and numbered lists, tables, links (http/https only) and [n] citations.
 */
(function (global) {
  "use strict";

  const escapeHtml = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  function inline(text, opts) {
    const stash = [];
    const keep = (html) => `\u0000${stash.push(html) - 1}\u0000`;

    let s = escapeHtml(text);
    s = s.replace(/`([^`\n]+)`/g, (_, code) => keep(`<code>${code}</code>`));
    s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) =>
      keep(`<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`));
    s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, "$1<em>$2</em>");
    s = s.replace(/(^|[^_\w])_([^_\n]+)_(?!\w)/g, "$1<em>$2</em>");
    // Citations like [1] or [1, 3] or [1][2]
    s = s.replace(/\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]/g, (_, nums) =>
      nums.split(",").map((n) => {
        n = n.trim();
        const known = !opts.sourceCount || Number(n) <= opts.sourceCount;
        return keep(`<button type="button" class="cite${known ? "" : " dangling"}" data-cite="${n}" aria-label="Show source ${n}">${n}</button>`);
      }).join(""));
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => stash[Number(i)]);
  }

  function isTableSep(line) {
    return /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line);
  }

  function splitRow(line) {
    return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
  }

  function render(src, opts) {
    opts = opts || {};
    const lines = String(src || "").replace(/\r\n/g, "\n").split("\n");
    const out = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Fenced code (an unterminated fence while streaming still renders)
      const fence = line.match(/^\s*```\s*([\w+-]*)\s*$/);
      if (fence) {
        const body = [];
        i++;
        while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) body.push(lines[i++]);
        i++;
        const lang = fence[1] ? ` data-lang="${escapeHtml(fence[1])}"` : "";
        out.push(`<pre${lang}><code>${escapeHtml(body.join("\n"))}</code></pre>`);
        continue;
      }

      if (!line.trim()) { i++; continue; }

      const heading = line.match(/^(#{1,6})\s+(.*)$/);
      if (heading) {
        const level = Math.min(4, Math.max(3, heading[1].length + 1));
        out.push(`<h${level}>${inline(heading[2], opts)}</h${level}>`);
        i++;
        continue;
      }

      // Table
      if (line.includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1])) {
        const head = splitRow(line);
        i += 2;
        const rows = [];
        while (i < lines.length && lines[i].includes("|") && lines[i].trim()) rows.push(splitRow(lines[i++]));
        out.push(
          "<table><thead><tr>" + head.map((h) => `<th>${inline(h, opts)}</th>`).join("") + "</tr></thead><tbody>" +
          rows.map((r) => "<tr>" + r.map((c) => `<td>${inline(c, opts)}</td>`).join("") + "</tr>").join("") +
          "</tbody></table>"
        );
        continue;
      }

      // Lists (one level; indented lines join the previous item)
      const listMatch = line.match(/^\s*([-*+]|\d+[.)])\s+(.*)$/);
      if (listMatch) {
        const ordered = /\d/.test(listMatch[1]);
        const start = ordered ? parseInt(listMatch[1], 10) : 1;
        const items = [];
        while (i < lines.length) {
          const m = lines[i].match(/^\s*([-*+]|\d+[.)])\s+(.*)$/);
          if (m && /\d/.test(m[1]) === ordered) { items.push(m[2]); i++; continue; }
          if (items.length && /^\s{2,}\S/.test(lines[i])) { items[items.length - 1] += " " + lines[i].trim(); i++; continue; }
          break;
        }
        const tag = ordered ? "ol" : "ul";
        const startAttr = ordered && start !== 1 ? ` start="${start}"` : "";
        out.push(`<${tag}${startAttr}>` + items.map((it) => `<li>${inline(it, opts)}</li>`).join("") + `</${tag}>`);
        continue;
      }

      // Paragraph: gather until a blank line or another block starts
      const para = [];
      while (
        i < lines.length && lines[i].trim() &&
        !/^\s*```/.test(lines[i]) && !/^#{1,6}\s/.test(lines[i]) && !/^\s*([-*+]|\d+[.)])\s+/.test(lines[i]) &&
        !(lines[i].includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1]))
      ) para.push(lines[i++]);
      out.push(`<p>${inline(para.join("\n"), opts).replace(/\n/g, "<br>")}</p>`);
    }
    return out.join("\n");
  }

  global.Markdown = { render, escapeHtml };
})(window);
