const STORAGE_KEY = 'javaCoach.conversations.v1';

const messagesEl = document.getElementById('messages');
const messagesInnerEl = document.getElementById('messages-inner');
const emptyState = document.getElementById('empty-state');
const topicInput = document.getElementById('topic-input');
const qbankBtn = document.getElementById('qbank-btn');
const topicsPanel = document.getElementById('topics-panel');
const newChatBtn = document.getElementById('new-chat-btn');
const composer = document.getElementById('composer');
const chatInput = document.getElementById('chat-input');
const questionCountEl = document.getElementById('question-count');
const conversationsEl = document.getElementById('conversations');

// ---------------- Persistence ----------------

function makeConversation() {
  const now = Date.now();
  return {
    id: `c_${now}_${Math.random().toString(36).slice(2, 8)}`,
    title: null, // set from the first user message
    messages: [], // {role, content}
    history: [], // {role, content} used as LLM context for free chat
    createdAt: now,
    updatedAt: now,
  };
}

function loadDb() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) throw new Error('empty');
    const db = JSON.parse(raw);
    if (!db.conversations || !db.conversations.length) throw new Error('no conversations');
    return db;
  } catch {
    const conv = makeConversation();
    return { conversations: [conv], activeId: conv.id };
  }
}

function saveDb() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch {
    // storage unavailable (private browsing, quota, etc.) - fail silently
  }
}

let db = loadDb();

function getActive() {
  return db.conversations.find((c) => c.id === db.activeId) || db.conversations[0];
}

function titleFrom(text) {
  const clean = text.replace(/\*\*/g, '').replace(/\s+/g, ' ').trim();
  return clean.length > 42 ? clean.slice(0, 42) + '…' : clean;
}

// ---------------- Rendering: messages ----------------

function renderMarkdown(text) {
  return window.marked ? marked.parse(text) : text.replace(/\n/g, '<br>');
}

function buildMessageEl(role, content, meta) {
  const wrap = document.createElement('div');
  wrap.className = `msg msg-${role}`;
  let metaHtml = '';
  if (meta && meta.sources && meta.sources.length) {
    metaHtml = `<div class="answer-meta">Sources: ${meta.sources.join(', ')} · Confidence: ${Math.round(meta.confidence * 100)}%</div>`;
  }
  wrap.innerHTML = `
    <div class="avatar">${role === 'user' ? '🧑' : '☕'}</div>
    <div class="bubble">${renderMarkdown(content)}${metaHtml}</div>
  `;
  return wrap;
}

function renderMessages() {
  messagesInnerEl.innerHTML = '';
  const conv = getActive();
  if (!conv.messages.length) {
    messagesInnerEl.appendChild(emptyState);
    return;
  }
  for (const m of conv.messages) {
    messagesInnerEl.appendChild(buildMessageEl(m.role, m.content, m.meta));
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addMessage(role, content, meta) {
  const conv = getActive();
  conv.messages.push({ role, content, meta });
  conv.updatedAt = Date.now();
  if (!conv.title && role === 'user') {
    conv.title = titleFrom(content);
  }
  if (emptyState.parentNode) emptyState.remove();
  messagesInnerEl.appendChild(buildMessageEl(role, content, meta));
  messagesEl.scrollTop = messagesEl.scrollHeight;
  saveDb();
  renderConversations();
}

function addTyping() {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-assistant';
  wrap.id = 'typing-indicator';
  wrap.innerHTML = `<div class="avatar">☕</div><div class="bubble typing"><span></span><span></span><span></span></div>`;
  messagesInnerEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function removeTyping() {
  document.getElementById('typing-indicator')?.remove();
}

// ---------------- Rendering: sidebar conversation list ----------------

function renderConversations() {
  conversationsEl.innerHTML = '';
  const sorted = [...db.conversations].sort((a, b) => b.updatedAt - a.updatedAt);
  for (const conv of sorted) {
    const item = document.createElement('div');
    item.className = 'conv-item' + (conv.id === db.activeId ? ' active' : '');
    item.innerHTML = `
      <span class="conv-title">${conv.title || 'New chat'}</span>
      <button class="conv-delete" type="button" aria-label="Delete chat">
        <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M6 7h12l-1 14H7L6 7zm3-3h6l1 2H8l1-2zM9 10v8m6-8v8" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round"/></svg>
      </button>
    `;
    item.querySelector('.conv-title').addEventListener('click', () => switchConversation(conv.id));
    item.querySelector('.conv-delete').addEventListener('click', (e) => {
      e.stopPropagation();
      deleteConversation(conv.id);
    });
    conversationsEl.appendChild(item);
  }
}

// ---------------- Conversation actions ----------------

function switchConversation(id) {
  db.activeId = id;
  saveDb();
  renderMessages();
  renderConversations();
}

function createConversation() {
  const conv = makeConversation();
  db.conversations.push(conv);
  db.activeId = conv.id;
  saveDb();
  renderMessages();
  renderConversations();
  chatInput.focus();
}

function deleteConversation(id) {
  db.conversations = db.conversations.filter((c) => c.id !== id);
  if (!db.conversations.length) {
    const conv = makeConversation();
    db.conversations.push(conv);
    db.activeId = conv.id;
  } else if (db.activeId === id) {
    db.activeId = [...db.conversations].sort((a, b) => b.updatedAt - a.updatedAt)[0].id;
  }
  saveDb();
  renderMessages();
  renderConversations();
}

// ---------------- Bot actions ----------------

function setBusy(busy) {
  qbankBtn.disabled = busy;
  chatInput.disabled = busy;
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Something went wrong.');
  }
  return res.json();
}

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Something went wrong.');
  }
  return res.json();
}

async function askQuestion(questionText) {
  topicsPanel.hidden = true;
  topicInput.value = '';
  await handleChat(questionText);
}

async function handleChat(text) {
  const conv = getActive();
  addMessage('user', text);
  addTyping();
  setBusy(true);
  try {
    const data = await postJSON('/api/chat', { message: text, history: conv.history });
    removeTyping();
    addMessage('assistant', data.reply, { sources: data.sources, confidence: data.confidence });
    conv.history.push({ role: 'user', content: text });
    conv.history.push({ role: 'assistant', content: data.reply });
    saveDb();
  } catch (e) {
    removeTyping();
    addMessage('assistant', `⚠️ ${e.message}`);
  } finally {
    setBusy(false);
  }
}

// ---------------- Question bank picker ----------------

let topicsCache = null;

async function loadTopics() {
  if (topicsCache) return topicsCache;
  const data = await getJSON('/api/topics');
  topicsCache = data.topics;
  return topicsCache;
}

function renderTopicList(topics) {
  topicsPanel.innerHTML = '';
  for (const topic of topics) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'topic-chip';
    chip.textContent = topic;
    chip.addEventListener('click', () => showQuestionsForTopic(topic));
    topicsPanel.appendChild(chip);
  }
}

function renderQuestionList(questions, backLabel) {
  topicsPanel.innerHTML = '';

  const back = document.createElement('button');
  back.type = 'button';
  back.className = 'panel-back';
  back.textContent = `← ${backLabel}`;
  back.addEventListener('click', showTopicList);
  topicsPanel.appendChild(back);

  if (!questions.length) {
    const empty = document.createElement('p');
    empty.className = 'panel-empty';
    empty.textContent = 'No questions found.';
    topicsPanel.appendChild(empty);
    return;
  }

  for (const q of questions) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'question-row';
    row.innerHTML = `<span>${q.question}</span><span class="question-difficulty">${q.difficulty}</span>`;
    row.addEventListener('click', () => askQuestion(q.question));
    topicsPanel.appendChild(row);
  }
}

async function showTopicList() {
  const topics = await loadTopics();
  renderTopicList(topics);
}

async function showQuestionsForTopic(topic) {
  const data = await getJSON(`/api/questions?topic=${encodeURIComponent(topic)}`);
  renderQuestionList(data.questions, 'Topics');
}

async function showQuestionsForQuery(query) {
  const data = await getJSON(`/api/questions?query=${encodeURIComponent(query)}`);
  renderQuestionList(data.questions, 'Topics');
}

async function toggleTopicsPanel() {
  if (!topicsPanel.hidden) {
    topicsPanel.hidden = true;
    return;
  }
  await showTopicList();
  topicsPanel.hidden = false;
}

// ---------------- Event wiring ----------------

qbankBtn.addEventListener('click', toggleTopicsPanel);

topicInput.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;
  const query = topicInput.value.trim();
  if (query) {
    showQuestionsForQuery(query);
    topicsPanel.hidden = false;
  }
});

document.querySelectorAll('.suggestion-chip').forEach((chip) => {
  chip.addEventListener('click', () => handleChat(chip.dataset.text));
});

newChatBtn.addEventListener('click', createConversation);

composer.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = '';
  handleChat(text);
});

fetch('/api/status')
  .then((r) => r.json())
  .then((data) => {
    questionCountEl.textContent = `${data.question_count} questions loaded`;
  })
  .catch(() => {
    questionCountEl.textContent = '';
  });

// ---------------- Initial render ----------------

renderMessages();
renderConversations();
