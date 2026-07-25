/**
 * Chat feature - Message handling, streaming, and chat management.
 */

import { getApiBaseUrl, apiFetch, streamChatCompletion, parseSSE, ApiError } from '../../shared/http.js';
import { showToast, showError } from '../../shared/toast.js';
import { escapeHtml, formatTime, nowTime, formatBytes, extOf } from '../../shared/utils.js';
import { renderMarkdown, renderMarkdownStream } from '../../shared/markdown.js';
import {
  getMessages, setMessages, getActiveChatId, setActiveChatId,
  getSelectedModel, selectModel, getModels, getAttachedFiles, setAttachedFiles,
  getLastUserText, setLastUserText, getIsGenerating, setIsGenerating,
  getAbortController, setAbortController, getWebSearchEnabled,
  getMaxTokens, getReasoningEffort, getTemperature,
  getChats, setChats,
  resetChatState
} from '../../core/state.js';
import { PROVIDER_COLORS, FILE_ICON_MAP } from '../../shared/constants.js';

// DOM elements
let elements = {};

// Monotonic generation counter — prevents a stale minimum-duration
// pause in one runGeneration() from resetting the button while a
// newer generation is already in progress.
let _genCounter = 0;

/**
 * Initialize DOM references.
 */
export function initElements() {
  elements = {
    chatScroll: $('#chatScroll'),
    chatColumn: $('#chatColumn'),
    welcomeScreen: $('#welcomeScreen'),
    messages: $('#messages'),
    skeletonWrap: $('#skeletonWrap'),
    errorState: $('#errorState'),
    errorDetailToggle: $('#errorDetailToggle'),
    retryBtn: $('#retryBtn'),
    scrollBottomBtn: $('#scrollBottomBtn'),
    backendDownState: $('#backendDownState'),
    fileChips: $('#fileChips'),
    attachBtn: $('#attachBtn'),
    fileInput: $('#fileInput'),
    messageInput: $('#messageInput'),
    sendBtn: $('#sendBtn'),
    stopBtn: $('#stopBtn'),
    webSearchToggle: $('#webSearchToggle'),
    tempControl: $('#tempControl'),
    tempPopover: $('#tempPopover'),
    tempSlider: $('#tempSlider'),
    tempValue: $('#tempValue'),
    tempPopoverValue: $('#tempPopoverValue'),
    tokenBtn: $('#tokenBtn'),
    tokenLabel: $('#tokenLabel'),
    tokenDropdown: $('#tokenDropdown'),
    tokenSelect: $('#tokenSelect'),
    reasoningBtn: $('#reasoningBtn'),
    reasoningLabel: $('#reasoningLabel'),
    reasoningDropdown: $('#reasoningDropdown'),
    reasoningSelect: $('#reasoningSelect'),
  };
}

/**
 * Set unified send/stop button visual state.
 * - idle:       accent bg, ▲ send-arrow (sendBtn visible, stopBtn hidden)
 * - generating: red bg, ⏹ stop icon   (stopBtn visible, sendBtn hidden)
 *
 * Uses TWO separate buttons and toggles visibility — eliminates all
 * CSS-cascade issues, transition blending, and class-toggling bugs.
 */
function setSendButtonState(generating) {
  const sendBtn = document.getElementById('sendBtn');
  const stopBtn = document.getElementById('stopBtn');
  if (!sendBtn || !stopBtn) return;

  if (generating) {
    sendBtn.style.display = 'none';
    stopBtn.style.display = '';
    document.title = '🔴 Generating… — Nexus';
  } else {
    sendBtn.style.display = '';
    stopBtn.style.display = 'none';
    document.title = 'Nexus — Universal AI Chat Platform';
  }
}

/**
 * Show or update the reasoning/thinking section inside an assistant message node.
 * Reasoning content is rendered as a collapsible <details> block above the
 * content area. It is ephemeral — not stored in message history.
 */
function showReasoningInNode(node, text) {
  let section = node.querySelector('.msg-reasoning');
  if (!section) {
    section = document.createElement('div');
    section.className = 'msg-reasoning';
    section.innerHTML = `<details open>
      <summary><i class="fa-solid fa-brain"></i> Reasoning</summary>
      <div class="msg-reasoning-content"></div>
    </details>`;
    const body = node.querySelector('.msg-body');
    const ref = body.querySelector('.msg-content') || body.querySelector('.typing-indicator');
    if (ref) {
      body.insertBefore(section, ref);
    } else {
      body.appendChild(section);
    }
  }
  const contentEl = section.querySelector('.msg-reasoning-content');
  if (contentEl) contentEl.textContent = text;
}

/**
 * Get provider display info for a model.
 */
function getProviderInfo(model) {
  const providerId = model?.provider;
  if (!providerId) return { label: 'Unknown', state: 'offline', color: '#9AA1AC' };
  return {
    label: providerId,
    state: 'online',
    color: PROVIDER_COLORS[providerId] || '#9AA1AC',
  };
}

/**
 * Build a message DOM node for rendering.
 */
export function buildMessageNode(msg) {
  const isUser = msg.role === 'user';

  if (isUser) {
    const node = document.createElement('div');
    node.className = 'msg user';
    node.dataset.id = msg.id || '';
    node.innerHTML = `
      <div class="msg-avatar"><i class="fa-solid fa-user"></i></div>
      <div class="msg-body">
        <div class="msg-meta"><span class="msg-author">You</span><span class="msg-time">${formatTime(msg.created_at)}</span></div>
        <div class="msg-content">${escapeHtml(msg.content)}</div>
      </div>`;
    return node;
  }

  // Assistant message
  const node = document.createElement('div');
  node.className = 'msg assistant';
  node.dataset.id = msg.id || '';

  const model = getSelectedModel();
  const info = getProviderInfo(model);
  node.style.setProperty('--provider-color', info.color);

  node.innerHTML = `
    <div class="msg-avatar" style="color:${info.color}"><i class="fa-solid fa-sparkles"></i></div>
    <div class="msg-body">
      <div class="msg-meta">
        <span class="msg-author">${escapeHtml(model?.name || msg.model || 'Assistant')}</span>
        <span class="msg-provider-tag" style="color:${info.color}">${escapeHtml(info.label)}</span>
        <span class="msg-time">${formatTime(msg.created_at)}</span>
      </div>
      <div class="msg-content">${msg.content ? renderMarkdown(msg.content) : ''}</div>
      <div class="msg-actions always-visible">
        <button class="msg-action-btn copy-msg-btn"><i class="fa-regular fa-copy"></i> Copy</button>
        <button class="msg-action-btn regenerate-btn"><i class="fa-solid fa-arrow-rotate-right"></i> Regenerate</button>
        <button class="msg-action-btn"><i class="fa-regular fa-thumbs-up"></i></button>
        <button class="msg-action-btn"><i class="fa-regular fa-thumbs-down"></i></button>
      </div>
    </div>`;

  // Copy button
  const copyBtn = node.querySelector('.copy-msg-btn');
  copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(msg.content || '').then(() => {
      copyBtn.classList.add('copied');
      copyBtn.innerHTML = `<i class="fa-solid fa-check"></i> Copied`;
      setTimeout(() => {
        copyBtn.classList.remove('copied');
        copyBtn.innerHTML = `<i class="fa-regular fa-copy"></i> Copy`;
      }, 1600);
    });
  });

  // Regenerate button
  const regenBtn = node.querySelector('.regenerate-btn');
  regenBtn.addEventListener('click', () => regenerate());

  return node;
}

/**
 * Render all messages to the DOM.
 */
export function renderMessages() {
  const messages = getMessages();
  const container = elements.messages;
  if (!container) return;

  container.innerHTML = '';
  messages.forEach((m) => container.appendChild(buildMessageNode(m)));
}

/**
 * Scroll to bottom of chat.
 */
export function scrollToBottom(smooth = true) {
  const scrollEl = elements.chatScroll;
  if (!scrollEl) return;
  scrollEl.scrollTo({ top: scrollEl.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
}

/**
 * Scroll to bottom if near bottom.
 */
export function scrollToBottomIfNearBottom() {
  const scrollEl = elements.chatScroll;
  if (!scrollEl) return;

  const dist = scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight;
  if (dist < 220) scrollToBottom(false);
}

/**
 * Handle file attachments - render file chips.
 */
export function renderFileChips() {
  const container = elements.fileChips;
  if (!container) return;

  const files = getAttachedFiles();
  container.innerHTML = '';

  files.forEach((f) => {
    const info = FILE_ICON_MAP[f.ext] || { icon: 'fa-file', color: '#9AA1AC' };
    const chip = document.createElement('div');
    chip.className = 'file-chip';
    chip.innerHTML = `
      <span class="file-chip-icon" style="background:${info.color}"><i class="fa-solid ${f.uploading ? 'fa-spinner fa-spin' : info.icon}"></i></span>
      <span class="file-chip-info">
        <span class="file-chip-name">${escapeHtml(f.name)}</span>
        <span class="file-chip-size">${f.uploading ? 'Uploading…' : formatBytes(f.size)}</span>
      </span>
      <button class="file-chip-remove" aria-label="Remove file"><i class="fa-solid fa-xmark"></i></button>
    `;

    chip.querySelector('.file-chip-remove').addEventListener('click', () => {
      const updated = getAttachedFiles().filter((x) => x.localId !== f.localId);
      setAttachedFiles(updated);
      renderFileChips();
    });

    container.appendChild(chip);
  });
}

/**
 * Handle file selection and upload.
 */
export async function handleFileSelection(fileList) {
  const accepted = [];
  let rejected = 0;

  Array.from(fileList).forEach((file) => {
    const ext = extOf(file.name);
    if (!FILE_ICON_MAP[ext]) {
      rejected++;
      return;
    }
    accepted.push(file);
  });

  if (rejected) showToast({ type: 'error', title: 'Unsupported file type', message: `${rejected} file(s) skipped.` });

  for (const file of accepted) {
    const localId = `local_${Math.random().toString(36).slice(2, 9)}`;
    const placeholder = { localId, id: null, name: file.name, size: file.size, ext: extOf(file.name), uploading: true };
    setAttachedFiles([...getAttachedFiles(), placeholder]);
    renderFileChips();

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await apiFetch('/files', { method: 'POST', body: form });
      const data = await res.json();

      const newFiles = getAttachedFiles().map((f) =>
        f.localId === localId ? { ...f, id: data.file_id, size: data.size_bytes, uploading: false } : f
      );
      setAttachedFiles(newFiles);
      renderFileChips();
    } catch (err) {
      const newFiles = getAttachedFiles().filter((f) => f.localId !== localId);
      setAttachedFiles(newFiles);
      renderFileChips();
      showToast({ type: 'error', title: `Upload failed: ${file.name}`, message: err.message });
    }
  }
}

/**
 * Sending a message - main entry point.
 */
export function handleSend() {
  const text = elements.messageInput?.value.trim() || '';
  const files = getAttachedFiles();

  if (!text && files.length === 0) return;
  if (getIsGenerating()) return;
  if (!getSelectedModel()) {
    showToast({ type: 'info', title: 'Select a provider', message: 'Start Ollama or link a provider key before sending a message.' });
    return;
  }
  if (files.some((f) => f.uploading)) {
    showToast({ type: 'info', message: 'Still uploading a file — one moment.' });
    return;
  }

  elements.welcomeScreen?.classList.add('hidden');

  const userMsg = { role: 'user', content: text || '(Sent with attached files)', created_at: new Date().toISOString() };
  setMessages([...getMessages(), userMsg]);
  elements.messages?.appendChild(buildMessageNode(userMsg));
  setLastUserText(userMsg.content);

  elements.messageInput.value = '';
  autoResizeTextarea();

  const fileIds = files.map((f) => f.id).filter(Boolean);
  setAttachedFiles([]);
  renderFileChips();
  scrollToBottom(true);

  runGeneration({ content: userMsg.content, fileIds, regenerate: false });
}

/**
 * Regenerate last assistant response.
 */
export function regenerate() {
  if (getIsGenerating() || !getLastUserText()) return;
  if (!getSelectedModel()) {
    showToast({ type: 'info', title: 'Model required', message: 'Select a model before regenerating.' });
    return;
  }

  // Remove last assistant message
  const msgs = getMessages();
  const lastIdx = msgs.findLastIndex((m) => m.role === 'assistant');
  if (lastIdx !== -1) {
    const updated = msgs.slice(0, lastIdx);
    setMessages(updated);
    renderMessages();
  }

  runGeneration({ content: getLastUserText(), fileIds: [], regenerate: true });
}

/**
 * Core generation logic with SSE streaming.
 */
export async function runGeneration({ content, fileIds, regenerate }) {
  const model = getSelectedModel();
  if (!model) {
    showToast({ type: 'info', title: 'Model required', message: 'Select a model before sending a message.' });
    return;
  }

  setIsGenerating(true);
  setSendButtonState(true);
  // Yield to the browser so it can paint the stop-button generating
  // state BEFORE any stream I/O begins. Without this macrotask, the
  // entire fetch + for-await-of loop can resolve in microtasks
  // (especially when the response arrives as a single chunk), and the
  // browser never gets a paint cycle — it sees the idle state only.
  await new Promise((r) => setTimeout(r, 0));

  // Record when the generating state was set so we can enforce a
  // minimum display duration — guarantees the stop button stays
  // visible long enough for the user to notice even on instant
  // responses. 2000 ms ensures it's impossible to miss (a human
  // blink is ~150 ms, reaction time ~200-300 ms).
  const genStartedAt = Date.now();
  const genId = ++_genCounter;
  const MIN_STOP_VISIBLE_MS = 2000;

  elements.errorState?.classList.add('hidden');
  const info = getProviderInfo(model);

  // Show typing indicator
  const typingNode = document.createElement('div');
  typingNode.className = 'msg assistant';
  typingNode.style.setProperty('--provider-color', info.color);
  typingNode.innerHTML = `
    <div class="msg-avatar" style="color:${info.color}"><i class="fa-solid fa-sparkles"></i></div>
    <div class="msg-body">
      <div class="msg-meta"><span class="msg-author">${escapeHtml(model.name)}</span><span class="msg-provider-tag" style="color:${info.color}">${escapeHtml(info.label)}</span></div>
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    </div>`;
  elements.messages?.appendChild(typingNode);
  scrollToBottom(true);

  const controller = new AbortController();
  setAbortController(controller);

  const body = {
    chat_id: getActiveChatId(),
    model: model.id,
    messages: getMessages().map(({ role, content }) => ({ role, content })),
    file_ids: fileIds,
    temperature: getTemperature(),
    max_tokens: parseInt(getMaxTokens(), 10),
    reasoning_effort: getReasoningEffort() === 'none' ? null : getReasoningEffort(),
    regenerate,
    web_search: getWebSearchEnabled(),
  };

  let collected = '';
  let reasoningContent = '';
  let sawFirstToken = false;
  let newChatId = null;
  let streamError = null;

  try {
    const stream = await streamChatCompletion(body, controller.signal);

    for await (const { event, data } of parseSSE(stream)) {
      if (event === 'error') {
        streamError = data;
        continue;
      }
      if (event === 'chat_id') {
        newChatId = data;
        continue;
      }
      if (event === 'reasoning') {
        reasoningContent += data;
        showReasoningInNode(typingNode, reasoningContent);
        continue;
      }
      if (data === '[DONE]') continue;

      if (!sawFirstToken) {
        sawFirstToken = true;
        const metaEl = typingNode.querySelector('.msg-meta');
        if (metaEl) metaEl.insertAdjacentHTML('beforeend', `<span class="msg-time">${nowTime()}</span>`);
        const indicator = typingNode.querySelector('.typing-indicator');
        if (indicator) indicator.outerHTML = '<div class="msg-content"><span class="stream-cursor"></span></div>';
      }

      collected += data;
      const contentEl = typingNode.querySelector('.msg-content');
      if (contentEl) {
        contentEl.innerHTML = escapeHtml(collected).replace(/\n/g, '<br>') + '<span class="stream-cursor"></span>';
      }
      scrollToBottomIfNearBottom();
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      streamError = null;
    } else if (err instanceof ApiError) {
      streamError = err.message;
    } else {
      streamError = err.message;
    }
  }

  try {
    if (streamError) {
      typingNode.remove();
      elements.errorState?.classList.remove('hidden');
      const providerLabel = info.label || model.provider || 'Provider';
      const modelName = model.name || 'Unknown model';
      elements.errorState.querySelector('strong').textContent = `${providerLabel} — ${modelName} returned an error`;

      let guidance = streamError;
      const errLow = streamError.toLowerCase();
      if (errLow.includes('not available') || errLow.includes('model not found') || errLow.includes('does not exist') || errLow.includes('subscription')) {
        guidance = `The model "${modelName}" is not available on ${providerLabel}. It may require a different subscription or have been deprecated. Try selecting a different model.`;
      } else if (errLow.includes('invalid') || errLow.includes('expired') || errLow.includes('authentication') || errLow.includes('unauthorized') || errLow.includes('401') || errLow.includes('no api key')) {
        guidance = `Your API key for ${providerLabel} appears to be invalid or missing. Open Settings → add or update your ${providerLabel} key.`;
      } else if (errLow.includes('rate') || errLow.includes('429') || errLow.includes('quota')) {
        guidance = `${providerLabel} rate limit or quota exceeded. Wait a moment and retry, or check your ${providerLabel} plan for usage limits.`;
      } else if (errLow.includes('timeout') || errLow.includes('timed out')) {
        guidance = `${providerLabel} took too long to respond. Try a smaller model or reduce the max tokens setting.`;
      } else if (errLow.includes('context') || errLow.includes('length') || errLow.includes('token')) {
        guidance = `The conversation is too long for ${modelName}. Start a new chat or reduce the message history.`;
      }
      elements.errorState.querySelector('p').textContent = guidance;
      elements.errorState.querySelector('.error-detail').textContent = streamError;

      // Add settings link in error
      const btnWrapper = elements.errorState.querySelector('.error-btns');
      if (btnWrapper && !btnWrapper.querySelector('.error-settings-link')) {
        const link = document.createElement('button');
        link.className = 'btn-secondary error-settings-link';
        link.textContent = 'Open Settings';
        link.addEventListener('click', () => {
          import('../../features/settings/settings.js').then(m => m.openSettings());
        });
        btnWrapper.appendChild(link);
      }
      scrollToBottom(true);

      // If model inaccessible, refresh models
      if (errLow.includes('not available') || errLow.includes('model not found') || errLow.includes('does not exist')) {
        // This will be handled by the models module
      }
    } else if (collected) {
      // Save chat ID on success
      if (newChatId && !getActiveChatId()) {
        setActiveChatId(newChatId);
      }
      // Reload chat list
      const sidebarModule = await import('../sidebar/sidebar.js');
      sidebarModule.loadChatList();
      const finalMsg = { role: 'assistant', content: collected, model: model.id, created_at: new Date().toISOString() };
      setMessages([...getMessages(), finalMsg]);
      typingNode.replaceWith(buildMessageNode(finalMsg));
    } else if (!sawFirstToken && !streamError) {
      // Aborted before any token
      typingNode.remove();
      showToast({ type: 'info', title: 'Generation stopped' });
    }
  } catch (_err) {
    showToast({ type: 'error', title: 'Unexpected error', message: _err.message });
  }

  setIsGenerating(false);
  setAbortController(null);

  // Enforce minimum stop-button visibility so the user always sees
  // the generating state, even on instant responses.
  const elapsed = Date.now() - genStartedAt;
  if (elapsed < MIN_STOP_VISIBLE_MS) {
    await new Promise((r) => setTimeout(r, MIN_STOP_VISIBLE_MS - elapsed));
  }
  // ALWAYS yield to the browser (macrotask) so it can paint the
  // generating state.  Without this, when elapsed >= MIN_STOP_VISIBLE_MS
  // the revert runs in the same microtask chain as stream completion
  // and the browser never paints the stop state — it only sees idle.
  await new Promise((r) => setTimeout(r, 16));

  // Only reset the button if we're still the most recent generation
  // — prevents a stale minimum-duration pause from stealing the
  // stop state from a newer generation.
  if (genId === _genCounter) {
    setSendButtonState(false);
  }
  scrollToBottomIfNearBottom();
}

/**
 * Auto-resize textarea.
 */
export function autoResizeTextarea() {
  const ta = elements.messageInput;
  if (!ta) return;
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
}

/**
 * Stop generation by aborting the current request.
 */
export function stopGeneration() {
  const ac = getAbortController();
  if (ac) ac.abort();
}

/**
 * Start a new chat.
 */
export async function startNewChat() {
  if (getIsGenerating() && getAbortController()) {
    getAbortController().abort();
  }
  resetChatState();
  setSendButtonState(false);
  const sidebarModule = await import('../sidebar/sidebar.js');
  sidebarModule.renderChatHistory(document.getElementById('searchChats')?.value || '');
  elements.errorState?.classList.add('hidden');
  elements.backendDownState?.classList.add('hidden');
  elements.skeletonWrap?.classList.add('hidden');
  elements.messages?.classList.remove('hidden');
  elements.messages.innerHTML = '';
  elements.welcomeScreen?.classList.remove('hidden');
  elements.messageInput.value = '';
  autoResizeTextarea();
  elements.messageInput?.focus();
}

/**
 * Initialize chat event listeners.
 */
export function initChatEvents() {
  initElements();

  // Send button — always sends a message.
  elements.sendBtn?.addEventListener('click', () => {
    handleSend();
  });

  // Stop button — always aborts the current generation.
  elements.stopBtn?.addEventListener('click', stopGeneration);
  elements.retryBtn?.addEventListener('click', () => {
    elements.errorState?.classList.add('hidden');
    if (!getSelectedModel()) {
      showToast({ type: 'info', title: 'Model required', message: 'Select a model before retrying.' });
      return;
    }
    if (getLastUserText()) runGeneration({ content: getLastUserText(), fileIds: [], regenerate: true });
  });
  elements.attachBtn?.addEventListener('click', () => elements.fileInput?.click());
  elements.fileInput?.addEventListener('change', (e) => { handleFileSelection(e.target.files); e.target.value = ''; });

  elements.messageInput?.addEventListener('input', autoResizeTextarea);
  elements.messageInput?.addEventListener('keydown', (e) => {
    // Ctrl/Cmd+Enter always sends
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleSend(); }
    // Enter without Shift sends on desktop (> 900px)
    else if (e.key === 'Enter' && !e.shiftKey && window.innerWidth > 900) { e.preventDefault(); handleSend(); }
    // On mobile/tablet, Shift+Enter sends, plain Enter creates newlines
    else if (e.key === 'Enter' && e.shiftKey && window.innerWidth <= 900) { e.preventDefault(); handleSend(); }
  });

  // Web search toggle
  elements.webSearchToggle?.addEventListener('click', () => {
    // State managed in core/state.js
    elements.webSearchToggle.classList.toggle('active');
    elements.webSearchToggle.setAttribute('aria-pressed', String(elements.webSearchToggle.classList.contains('active')));
  });

  // Composer drag-drop
  const composerEl = document.getElementById('composer');
  ['dragover', 'dragenter'].forEach((evt) => composerEl?.addEventListener(evt, (e) => { e.preventDefault(); composerEl.style.borderColor = 'var(--accent)'; }));
  ['dragleave', 'drop'].forEach((evt) => composerEl?.addEventListener(evt, (e) => {
    e.preventDefault(); composerEl.style.borderColor = '';
    if (evt === 'drop' && e.dataTransfer.files.length) handleFileSelection(e.dataTransfer.files);
  }));

  // Suggestion cards
  document.querySelectorAll('.suggestion-card').forEach((card) => {
    card.addEventListener('click', () => {
      elements.messageInput.value = card.dataset.prompt;
      autoResizeTextarea();
      handleSend();
    });
  });

}