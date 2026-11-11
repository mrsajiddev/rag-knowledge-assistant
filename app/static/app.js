/* Nestora Assistant chat client: streaming answers, citations, local history. */
(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const els = {
    rail: $("#rail"), scrim: $("#scrim"), railOpen: $("#railOpen"), railClose: $("#railClose"),
    newChat: $("#newChat"), history: $("#history"), historyEmpty: $("#historyEmpty"), docs: $("#docs"),
    status: $("#status"), statusText: $("#statusText"), modelName: $("#modelName"), brandName: $("#brandName"),
    topbarTitle: $("#topbarTitle"), themeToggle: $("#themeToggle"),
    scroller: $("#scroller"), welcome: $("#welcome"), starters: $("#starters"), thread: $("#thread"),
    composer: $("#composer"), input: $("#input"), send: $("#send"), sourceTpl: $("#sourceTpl"),
  };

  const STARTERS = [
    { topic: "Pricing", q: "How much is the Growth plan, and what do I get over Starter?" },
    { topic: "Payouts", q: "When will I receive my NestPay payouts on the Starter plan?" },
    { topic: "Errors", q: "What does error NS-4012 mean and how do I fix it?" },
    { topic: "Webhooks", q: "How do I verify a webhook signature in Laravel?" },
    { topic: "Policy", q: "Can I get a refund on an annual plan?" },
    { topic: "Handbook", q: "How many days of annual leave do employees get?" },
  ];
  const STORE_KEY = "nestora.conversations.v1";
  const THEME_KEY = "nestora.theme";
  const MAX_SAVED = 30;

  // ------------------------------------------------------------------ storage
  const storage = {
    read(key, fallback) {
      try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
    },
    write(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode or quota: keep in memory */ }
    },
  };

  let conversations = storage.read(STORE_KEY, []);
  let current = null;        // { id, title, messages: [{role, content, sources?, timing?, error?}] }
  let controller = null;     // AbortController of the running request

  const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  const save = () => {
    conversations = conversations.filter((c) => c.messages.length).slice(0, MAX_SAVED);
    storage.write(STORE_KEY, conversations);
  };

  // ------------------------------------------------------------------ theme
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    els.themeToggle.setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
  }
  const preferred = storage.read(THEME_KEY, null) ||
    (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(preferred);
  els.themeToggle.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    storage.write(THEME_KEY, next);
  });

  // ------------------------------------------------------------------ rail
  const openRail = () => { els.rail.classList.add("open"); els.scrim.hidden = false; };
  const closeRail = () => { els.rail.classList.remove("open"); els.scrim.hidden = true; };
  els.railOpen.addEventListener("click", openRail);
  els.railClose.addEventListener("click", closeRail);
  els.scrim.addEventListener("click", closeRail);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeRail(); });

  function renderHistory() {
    els.history.innerHTML = "";
    els.historyEmpty.hidden = conversations.length > 0;
    for (const conv of conversations) {
      const li = document.createElement("li");
      li.className = "history-item" + (current && conv.id === current.id ? " active" : "");
      const open = document.createElement("button");
      open.type = "button"; open.className = "open"; open.textContent = conv.title; open.title = conv.title;
      open.addEventListener("click", () => { loadConversation(conv.id); closeRail(); });
      const del = document.createElement("button");
      del.type = "button"; del.className = "delete"; del.setAttribute("aria-label", `Delete "${conv.title}"`);
      del.innerHTML = '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>';
      del.addEventListener("click", () => {
        conversations = conversations.filter((c) => c.id !== conv.id);
        save();
        if (current && current.id === conv.id) startConversation();
        renderHistory();
      });
      li.append(open, del);
      els.history.append(li);
    }
  }

  function renderDocs(docs) {
    els.docs.innerHTML = "";
    if (!docs.length) {
      els.docs.innerHTML = '<li><span>No documents indexed yet. Run <code>python -m app.ingest</code>.</span></li>';
      return;
    }
    let lastGroup = "";
    for (const doc of docs) {
      const group = doc.source.includes("/") ? doc.source.split("/")[0] : "";
      if (group !== lastGroup) {
        const g = document.createElement("li");
        g.className = "group";
        g.textContent = group.charAt(0).toUpperCase() + group.slice(1);
        els.docs.append(g);
        lastGroup = group;
      }
      const li = document.createElement("li");
      li.title = doc.source;
      li.innerHTML = `<span></span><span class="count"></span>`;
      li.firstChild.textContent = doc.title;
      li.lastChild.textContent = doc.chunks;
      li.lastChild.setAttribute("aria-label", `${doc.chunks} passages`);
      els.docs.append(li);
    }
  }

  // ------------------------------------------------------------------ status
  async function loadStatus() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      if (data.app_name) { els.brandName.textContent = data.app_name; document.title = data.app_name; }
      els.modelName.textContent = `${data.llm.model} with ${data.embeddings.model}`;
      if (data.ready) {
        els.status.className = "status ok";
        els.statusText.textContent = `${data.chunks} passages indexed`;
      } else {
        els.status.className = "status bad";
        els.statusText.textContent = data.error ? "Vector database offline" : "Knowledge base is empty";
      }
    } catch {
      els.status.className = "status bad";
      els.statusText.textContent = "Server unreachable";
    }
    try {
      const res = await fetch("/api/documents");
      if (res.ok) renderDocs((await res.json()).documents);
    } catch { /* status line already explains */ }
  }

  // ------------------------------------------------------------------ rendering
  function renderStarters() {
    els.starters.innerHTML = "";
    for (const s of STARTERS) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "starter";
      b.innerHTML = "<small></small><span></span>";
      b.firstChild.textContent = s.topic;
      b.lastChild.textContent = s.q;
      b.addEventListener("click", () => ask(s.q));
      els.starters.append(b);
    }
  }

  function scrollToEnd(force) {
    const el = els.scroller;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 160;
    if (force || nearBottom) el.scrollTop = el.scrollHeight;
  }

  function userNode(text) {
    const li = document.createElement("li");
    li.className = "msg-user";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    li.append(bubble);
    return li;
  }

  function botNode() {
    const li = document.createElement("li");
    li.className = "msg-bot";
    li.innerHTML = '<div class="thinking"><span class="bars"><i></i><i></i><i></i></span>Searching the knowledge base</div><div class="answer" hidden></div>';
    return li;
  }

  function fillBot(li, msg, streaming) {
    const thinking = li.querySelector(".thinking");
    const answer = li.querySelector(".answer");
    const sources = msg.sources || [];

    if (msg.content || !streaming) {
      if (thinking) thinking.remove();
      answer.hidden = false;
      answer.innerHTML = Markdown.render(msg.content, { sourceCount: sources.length });
      answer.classList.toggle("caret", Boolean(streaming));
    } else if (thinking && sources.length) {
      thinking.lastChild.textContent = `Found ${sources.length} relevant passage${sources.length === 1 ? "" : "s"}, writing an answer`;
    }

    if (msg.error) {
      let err = li.querySelector(".msg-error");
      if (!err) { err = document.createElement("div"); err.className = "msg-error"; li.append(err); }
      err.textContent = msg.error;
      if (!msg.content) answer.hidden = true;
    }

    if (!streaming) {
      if (sources.length && !li.querySelector(".sources")) li.append(sourcesNode(sources));
      if (!li.querySelector(".meta") && (msg.content || msg.error)) li.append(metaNode(msg));
    }
  }

  // Passages are shown as reading text, so drop Markdown emphasis and link syntax.
  const plain = (md) => md
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`\n]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, "$1 ($2)");

  function sourcesNode(sources) {
    const wrap = document.createElement("div");
    wrap.className = "sources";
    const label = document.createElement("p");
    label.className = "sources-label";
    label.textContent = sources.length === 1 ? "1 source" : `${sources.length} sources`;
    const ol = document.createElement("ol");
    for (const src of sources) {
      const node = els.sourceTpl.content.firstElementChild.cloneNode(true);
      node.dataset.source = src.id;
      node.querySelector(".source-num").textContent = src.id;
      node.querySelector(".source-title").textContent = src.section ? `${src.title}: ${src.section}` : src.title;
      node.querySelector(".source-score").textContent = `${Math.round(src.score * 100)}% match`;
      node.querySelector(".source-path").textContent = src.source;
      const quote = document.createElement("span");
      quote.textContent = plain(src.text);
      node.querySelector(".source-text").append(quote);
      const head = node.querySelector(".source-head");
      head.addEventListener("click", () => toggleSource(node));
      ol.append(node);
    }
    wrap.append(label, ol);
    return wrap;
  }

  function toggleSource(node, open) {
    const head = node.querySelector(".source-head");
    const body = node.querySelector(".source-body");
    const next = open === undefined ? body.hidden : open;
    body.hidden = !next;
    head.setAttribute("aria-expanded", String(next));
  }

  function metaNode(msg) {
    const meta = document.createElement("div");
    meta.className = "meta";
    if (msg.timing && msg.timing.total_ms) {
      const t = document.createElement("span");
      t.textContent = `Answered in ${(msg.timing.total_ms / 1000).toFixed(1)} s`;
      meta.append(t);
    }
    if (msg.content) {
      const copy = document.createElement("button");
      copy.type = "button"; copy.textContent = "Copy answer";
      copy.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(msg.content); copy.textContent = "Copied"; }
        catch { copy.textContent = "Copy failed"; }
        setTimeout(() => (copy.textContent = "Copy answer"), 1500);
      });
      meta.append(copy);
    }
    return meta;
  }

  // Clicking a [n] marker opens that passage under the answer.
  els.thread.addEventListener("click", (e) => {
    const cite = e.target.closest(".cite");
    if (!cite) return;
    const msg = cite.closest(".msg-bot");
    const node = msg && msg.querySelector(`.source[data-source="${cite.dataset.cite}"]`);
    if (!node) return;
    toggleSource(node, true);
    node.classList.remove("flash"); void node.offsetWidth; node.classList.add("flash");
    setTimeout(() => node.classList.remove("flash"), 1200);
    node.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });

  function renderConversation() {
    els.thread.innerHTML = "";
    const msgs = current ? current.messages : [];
    els.welcome.hidden = msgs.length > 0;
    els.topbarTitle.textContent = current && current.messages.length ? current.title : "New conversation";
    for (const msg of msgs) {
      if (msg.role === "user") els.thread.append(userNode(msg.content));
      else { const li = botNode(); fillBot(li, msg, false); els.thread.append(li); }
    }
    renderHistory();
    scrollToEnd(true);
  }

  function startConversation() {
    if (controller) controller.abort();
    current = { id: newId(), title: "New conversation", messages: [] };
    renderConversation();
    els.input.focus();
  }

  function loadConversation(id) {
    if (controller) controller.abort();
    current = conversations.find((c) => c.id === id) || null;
    if (!current) return startConversation();
    renderConversation();
  }

  // ------------------------------------------------------------------ asking
  async function ask(question) {
    question = question.trim();
    if (!question || controller) return;
    if (!current) startConversation();

    const history = current.messages
      .filter((m) => !m.error && m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    if (!current.messages.length) {
      current.title = question.length > 60 ? question.slice(0, 57) + "..." : question;
      conversations.unshift(current);
    }
    current.messages.push({ role: "user", content: question });
    const bot = { role: "assistant", content: "", sources: [] };
    current.messages.push(bot);

    els.welcome.hidden = true;
    els.topbarTitle.textContent = current.title;
    els.thread.append(userNode(question));
    const li = botNode();
    els.thread.append(li);
    renderHistory();
    scrollToEnd(true);

    els.input.value = "";
    autosize();
    setBusy(true);
    controller = new AbortController();

    let frame = 0;
    const paint = () => { frame = 0; fillBot(li, bot, true); scrollToEnd(false); };

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history }),
        signal: controller.signal,
      });
      if (!res.ok) {
        let detail = `The server answered with status ${res.status}.`;
        try { const body = await res.json(); if (body.detail) detail = typeof body.detail === "string" ? body.detail : "The question was not accepted."; } catch { /* keep default */ }
        throw new Error(detail);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let cut;
        while ((cut = buffer.indexOf("\n\n")) >= 0) {
          const chunk = buffer.slice(0, cut);
          buffer = buffer.slice(cut + 2);
          const data = chunk.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim()).join("");
          if (!data) continue;
          const event = JSON.parse(data);
          if (event.type === "sources") bot.sources = event.sources;
          else if (event.type === "token") bot.content += event.text;
          else if (event.type === "done") bot.timing = event.timing;
          else if (event.type === "error") bot.error = event.message;
          if (!frame) frame = requestAnimationFrame(paint);
        }
      }
    } catch (err) {
      if (err.name === "AbortError") bot.error = bot.content ? null : "Stopped.";
      else bot.error = err.message || "Could not reach the server.";
    } finally {
      if (frame) cancelAnimationFrame(frame);
      controller = null;
      setBusy(false);
      if (!bot.content && !bot.error) bot.error = "The model returned an empty answer. Try asking again.";
      fillBot(li, bot, false);
      scrollToEnd(false);
      save();
      els.input.focus();
    }
  }

  // ------------------------------------------------------------------ composer
  function setBusy(busy) {
    els.composer.classList.toggle("busy", busy);
    els.send.setAttribute("aria-label", busy ? "Stop answering" : "Send question");
    els.send.disabled = !busy && !els.input.value.trim();
  }

  function autosize() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 200) + "px";
    if (!controller) els.send.disabled = !els.input.value.trim();
  }

  els.input.addEventListener("input", autosize);
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      els.composer.requestSubmit();
    }
  });
  els.composer.addEventListener("submit", (e) => {
    e.preventDefault();
    if (controller) { controller.abort(); return; }
    ask(els.input.value);
  });
  els.newChat.addEventListener("click", () => { startConversation(); closeRail(); });

  // ------------------------------------------------------------------ boot
  renderStarters();
  startConversation();
  setBusy(false);
  loadStatus();
})();
