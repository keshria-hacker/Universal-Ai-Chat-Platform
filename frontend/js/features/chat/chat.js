/**
 * Chat feature - Message handling, streaming, and chat management.
 */

import { getApiBaseUrl, apiFetch, streamChatCompletion, parseSSE, ApiError } from '../../shared/http.js';
import { showToast, showError } from '../../shared/toast.js';
import { escapeHtml, formatTime, nowTime, formatBytes, extOf } from '../../shared/utils.js';
import { renderMarkdown, renderMarkdownStream, finalizeMarkdownRender } from '../../shared/markdown.js';
import {
  getMessages, setMessages, getActiveChatId, setActiveChatId,
  getSelectedModel, selectModel, getModels, getAttachedFiles, setAttachedFiles,
  getLastUserText, setLastUserText, getIsGenerating, setIsGenerating,
  getAbortController, setAbortController, getWebSearchEnabled, setWebSearchEnabled,
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
 * Phase-aware response status helper.
 * Updates the assistant message node with the current response phase.
 */
function setThinkingPhase(node, phase, elapsedSec = null) {
  let statusEl = node.querySelector('.msg-phase-status');
  if (!statusEl) {
    statusEl = document.createElement('div');
    statusEl.className = 'msg-phase-status';
    const body = node.querySelector('.msg-body');
    const ref = body.querySelector('.msg-content') || body.querySelector('.typing-indicator');
    if (ref) {
      body.insertBefore(statusEl, ref);
    } else {
      body.appendChild(statusEl);
    }
  }

  const phases = {
    connecting: { text: 'Connecting…', icon: 'fa-solid fa-plug-circle-bolt' },
    thinking:   { text: 'Thinking…',   icon: 'fa-solid fa-brain' },
    writing:    { text: 'Writing…',    icon: 'fa-solid fa-pen-to-square' },
    done:       { text: 'Done',        icon: 'fa-solid fa-check' },
  };

  const p = phases[phase] || phases.connecting;
  let displayText = p.text;
  if (phase === 'done' && elapsedSec !== null) {
    displayText = `Done — ${elapsedSec}s`;
  }
  statusEl.className = `msg-phase-status ${phase}`;
  statusEl.innerHTML = `<i class="${p.icon}"></i><span>${displayText}</span>`;
  statusEl.setAttribute('aria-live', 'polite');
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
        <div class="msg-edit-btn" title="Edit message"><i class="fa-regular fa-pen-to-square"></i> Edit</div>
      </div>`;

    var editBtn = node.querySelector(".msg-edit-btn");
    if (editBtn) {
      editBtn.addEventListener("click", function() {
        var contentEl = node.querySelector(".msg-content");
        if (!contentEl) return;
        var origText = msg.content;
        var ta = document.createElement("textarea");
        ta.className = "msg-edit-textarea";
        ta.value = origText;
        contentEl.replaceWith(ta);
        editBtn.style.display = "none";

        var adiv = document.createElement("div");
        adiv.className = "msg-edit-actions";
        adiv.innerHTML = '<button class="msg-edit-save">Save</button><button class="msg-edit-cancel">Cancel</button>';
        ta.after(adiv);
        ta.focus();

        function doSave() {
          var nt = ta.value.trim();
          if (nt && nt !== origText) {
            msg.content = nt;
            var allMsgs = getMessages();
            var idx = allMsgs.indexOf(msg);
            if (idx !== -1) {
              setMessages(allMsgs.slice(0, idx + 1));
              renderMessages();
              setLastUserText(nt);
              setTimeout(function() { runGeneration({ content: nt, fileIds: [], regenerate: true }); }, 100);
            }
          } else { doCancel(); }
        }
        function doCancel() {
          var rst = document.createElement("div");
          rst.className = "msg-content";
          rst.innerHTML = escapeHtml(origText);
          ta.replaceWith(rst);
          editBtn.style.display = "";
          adiv.remove();
        }
        adiv.querySelector(".msg-edit-save").addEventListener("click", doSave);
        adiv.querySelector(".msg-edit-cancel").addEventListener("click", doCancel);
        ta.addEventListener("keydown", function(e) {
          if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); doSave(); }
          if (e.key === "Escape") { e.preventDefault(); doCancel(); }
        });
      });
    }
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
    <div class="msg-body">
      <div class="msg-meta">
        <span class="msg-author">${escapeHtml(model?.name || msg.model || 'Assistant')}</span>
        <span class="msg-provider-tag" style="color:${info.color}">${escapeHtml(info.label)}</span>
        <span class="msg-time">${formatTime(msg.created_at)}</span>
        ${msg.response_time != null ? `<span class="msg-response-time">${msg.response_time.toFixed(1)}s</span>` : ''}
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
  // Yield so the stop-button generating state paints before stream I/O begins
  await new Promise((r) => setTimeout(r, 0));

  const genStartedAt = Date.now();
  const genId = ++_genCounter;
  const MIN_STOP_VISIBLE_MS = 2000;

  elements.errorState?.classList.add('hidden');
  const info = getProviderInfo(model);

  // Initial assistant message node with CONNECTING phase
  const typingNode = document.createElement('div');
  typingNode.className = 'msg assistant';
  typingNode.style.setProperty('--provider-color', info.color);
  typingNode.innerHTML = `
    <div class="msg-avatar" style="color:${info.color}"><i class="fa-solid fa-sparkles"></i></div>
    <div class="msg-body">
      <div class="msg-meta"><span class="msg-author">${escapeHtml(model.name)}</span><span class="msg-provider-tag" style="color:${info.color}">${escapeHtml(info.label)}</span></div>
    </div>`;
  elements.messages?.appendChild(typingNode);
  scrollToBottom(true);

  var _thinkStartTime = Date.now();
  var _thinkTimer = null;
  function startElapsedTimer() {
    if (_thinkTimer) clearInterval(_thinkTimer);
    _thinkTimer = setInterval(function() {
      var elapsed = Math.floor((Date.now() - _thinkStartTime) / 1000);
      var phaseEl = typingNode.querySelector(".msg-phase-status");
      if (phaseEl) {
        var es = phaseEl.querySelector(".msg-thinking-elapsed");
        if (!es) { es = document.createElement("span"); es.className = "msg-thinking-elapsed"; phaseEl.appendChild(es); }
        es.textContent = elapsed + "s";
      }
    }, 1000);
  }

  var _thinkStartTime = Date.now();
  var _thinkTimer = null;
  function startElapsedTimer() {
    if (_thinkTimer) clearInterval(_thinkTimer);
    _thinkTimer = setInterval(function() {
      var elapsed = Math.floor((Date.now() - _thinkStartTime) / 1000);
      var phaseEl = typingNode.querySelector(".msg-phase-status");
      if (phaseEl) {
        var es = phaseEl.querySelector(".msg-thinking-elapsed");
        if (!es) { es = document.createElement("span"); es.className = "msg-thinking-elapsed"; phaseEl.appendChild(es); }
        es.textContent = elapsed + "s";
      }
    }, 1000);
  }

  // PHASE: Connecting
  setThinkingPhase(typingNode, 'connecting');
  startElapsedTimer();
  startElapsedTimer();

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
  let hasStartedWriting = false;
  let newChatId = null;
  let streamError = null;
  let streamStarted = false;

  try {
    const stream = await streamChatCompletion(body, controller.signal);
    streamStarted = true;

    // PHASE: Thinking — stream connected, waiting for first token
    setThinkingPhase(typingNode, 'thinking');

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

      // PHASE: Writing — first visible content token arrived
      if (!hasStartedWriting) {
        hasStartedWriting = true;
        setThinkingPhase(typingNode, 'writing');
      }

      collected += data;
      const contentEl = typingNode.querySelector('.msg-content');
      if (contentEl) {
        // Use streaming markdown renderer for visually stable incremental updates
        contentEl.innerHTML = renderMarkdownStream(collected) + '<span class="stream-cursor"></span>';
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

      if (errLow.includes('not available') || errLow.includes('model not found') || errLow.includes('does not exist')) {
        // handled by models module
      }
    } else if (collected) {
      // Save chat ID on success
      if (newChatId && !getActiveChatId()) {
        setActiveChatId(newChatId);
      }
      // Reload chat list
      const sidebarModule = await import('../sidebar/sidebar.js');
      sidebarModule.loadChatList();
      const elapsedMs = Date.now() - genStartedAt;
      const elapsedSec = (elapsedMs / 1000).toFixed(1);
      const finalMsg = { role: 'assistant', content: collected, model: model.id, created_at: new Date().toISOString(), response_time: parseFloat(elapsedSec) };
      setMessages([...getMessages(), finalMsg]);
      // PHASE: Done — show completion time briefly, then replace with final message
      setThinkingPhase(typingNode, 'done', elapsedSec);
      // Small delay so "Done — Xs" is visible before replace
      await new Promise((r) => setTimeout(r, 600));
      const finalNode = buildMessageNode(finalMsg);
      typingNode.replaceWith(finalNode);
      // Final render pass: ensure complete markdown with syntax highlighting
      await finalizeMarkdownRender(finalNode, collected);
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
  if (_thinkTimer) { clearInterval(_thinkTimer); _thinkTimer = null; }

  // Enforce minimum stop-button visibility
  const elapsed = Date.now() - genStartedAt;
  if (elapsed < MIN_STOP_VISIBLE_MS) {
    await new Promise((r) => setTimeout(r, MIN_STOP_VISIBLE_MS - elapsed));
  }
  await new Promise((r) => setTimeout(r, 16));

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
    const enabled = !getWebSearchEnabled();
    setWebSearchEnabled(enabled);
    elements.webSearchToggle.classList.toggle('active', enabled);
    elements.webSearchToggle.setAttribute('aria-pressed', String(enabled));
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


  // Token counter - live estimate
  var tokenCountEl = document.getElementById('tokenCounter');
  var msgInput = document.getElementById('messageInput');
  function updateTokenEstimate() {
    if (!tokenCountEl || !msgInput) return;
    var text = msgInput.value || '';
    var tokens = Math.ceil(text.length / 4);
    var maxTokens = 8192;
    var pct = tokens / maxTokens;
    tokenCountEl.textContent = tokens.toLocaleString() + ' / ' + maxTokens.toLocaleString() + ' tokens';
    tokenCountEl.className = 'token-counter';
    if (pct > 0.9) tokenCountEl.classList.add('danger');
    else if (pct > 0.7) tokenCountEl.classList.add('warning');
  }
  msgInput?.addEventListener('input', updateTokenEstimate);
  updateTokenEstimate();


  // Token counter - live estimate
  var tokenCountEl = document.getElementById('tokenCounter');
  var msgInput = document.getElementById('messageInput');
  function updateTokenEstimate() {
    if (!tokenCountEl || !msgInput) return;
    var text = msgInput.value || '';
    var tokens = Math.ceil(text.length / 4);
    var maxTokens = 8192;
    var pct = tokens / maxTokens;
    tokenCountEl.textContent = tokens.toLocaleString() + ' / ' + maxTokens.toLocaleString() + ' tokens';
    tokenCountEl.className = 'token-counter';
    if (pct > 0.9) tokenCountEl.classList.add('danger');
    else if (pct > 0.7) tokenCountEl.classList.add('warning');
  }
  msgInput?.addEventListener('input', updateTokenEstimate);
  updateTokenEstimate();

}