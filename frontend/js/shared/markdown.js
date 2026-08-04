/**
 * Markdown rendering with syntax highlighting.
 * Uses marked.js 15+ and highlight.js from CDN with DOMPurify sanitization.
 * Supports streaming incremental rendering and final enhanced render pass.
 */

import { escapeHtml } from './utils.js';

let _marked = null;
let _hljs = null;
let _DOMPurify = null;

/**
 * Check if markdown libraries are loaded.
 */
function checkLibraries() {
  if (typeof marked !== 'undefined') _marked = marked;
  if (typeof hljs !== 'undefined') _hljs = hljs;
  if (typeof DOMPurify !== 'undefined') _DOMPurify = DOMPurify;
}

/**
 * Configure marked.js 15+ with GFM options and custom renderers.
 */
function configureMarked() {
  if (!_marked || _marked.__nexusConfigured) return;

  // marked.js 15+ uses marked.use() for configuration
  _marked.use({
    gfm: true,
    breaks: true,
    pedantic: false,
    silent: false,
    async: false,
    // Custom renderer for security-sensitive elements
    renderer: {
      link(token) {
        if (!token.href) return token.text || '';
        const safeHref = token.href.startsWith('javascript:') ? '#' : token.href;
        const target = safeHref.startsWith('http') ? ' target="_blank" rel="noopener noreferrer"' : '';
        const titleAttr = token.title ? ` title="${escapeHtml(token.title)}"` : '';
        return `<a href="${escapeHtml(safeHref)}"${target}${titleAttr}>${this.parser.parseInline(token.tokens)}</a>`;
      },
      image(token) {
        if (!token.href) return '';
        const safeHref = token.href.startsWith('javascript:') ? '' : token.href;
        const titleAttr = token.title ? ` title="${escapeHtml(token.title)}"` : '';
        return `<img src="${escapeHtml(safeHref)}" alt="${escapeHtml(token.text || '')}"${titleAttr} loading="lazy">`;
      },
      codespan(token) {
        return `<code>${escapeHtml(token.text)}</code>`;
      },
      code(token) {
        const lang = token.lang && token.lang.trim() ? token.lang.trim() : 'text';
        const safeLang = escapeHtml(lang);
        const safeCode = escapeHtml(token.text);
        return `<pre><code class="language-${safeLang}">${safeCode}</code></pre>`;
      },
      blockquote(token) {
        return `<blockquote>${this.parser.parse(token.tokens)}</blockquote>`;
      },
      table(token) {
        // Build table with scroll wrapper
        const header = token.header || '';
        const rows = token.rows || [];
        return `<div class="table-scroll"><table><thead>${header}</thead><tbody>${rows}</tbody></table></div>`;
      },
      tablerow(token) {
        return `<tr>${this.parser.parseInline(token.tokens)}</tr>`;
      },
      tablecell(token) {
        const tag = token.header ? 'th' : 'td';
        const align = token.align ? ` style="text-align:${token.align}"` : '';
        return `<${tag}${align}>${this.parser.parseInline(token.tokens)}</${tag}>`;
      },
      hr() {
        return '<hr>';
      },
      heading(token) {
        return `<h${token.depth}>${this.parser.parseInline(token.tokens)}</h${token.depth}>`;
      },
      list(token) {
        const tag = token.ordered ? 'ol' : 'ul';
        const startAttr = token.ordered && token.start && token.start !== 1 ? ` start="${token.start}"` : '';
        return `<${tag}${startAttr}>${this.parser.parse(token.tokens)}</${tag}>`;
      },
      listitem(token) {
        if (token.task) {
          const checkAttr = token.checked ? ' checked' : '';
          return `<li class="task-list-item"><input type="checkbox" disabled${checkAttr}> ${this.parser.parseInline(token.tokens)}</li>`;
        }
        return `<li>${this.parser.parse(token.tokens)}</li>`;
      },
      paragraph(token) {
        return `<p>${this.parser.parseInline(token.tokens)}</p>`;
      },
      strong(token) {
        return `<strong>${this.parser.parseInline(token.tokens)}</strong>`;
      },
      em(token) {
        return `<em>${this.parser.parseInline(token.tokens)}</em>`;
      },
      del(token) {
        return `<del>${this.parser.parseInline(token.tokens)}</del>`;
      },
      text(token) {
        return escapeHtml(token.text);
      },
      br() {
        return '<br>';
      },
    },
  });

  _marked.__nexusConfigured = true;
}

/**
 * Parse markdown to sanitized HTML.
 * @param {string} markdown - Markdown text
 * @returns {string} - Sanitized HTML string
 */
export function parseMarkdown(markdown) {
  checkLibraries();
  configureMarked();

  if (!_marked?.parse) {
    // Fallback: escaped text with line breaks
    return escapeHtml(markdown || '').replace(/\n/g, '<br>');
  }

  try {
    const raw = _marked.parse(markdown || '');

    // Sanitize HTML to prevent XSS
    let safeHtml = raw;
    if (_DOMPurify?.sanitize) {
      safeHtml = _DOMPurify.sanitize(raw, {
        USE_PROFILES: { html: true },
        ALLOWED_TAGS: [
          'p', 'br', 'strong', 'em', 'del', 'code', 'pre', 'blockquote',
          'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
          'ul', 'ol', 'li', 'a', 'img', 'hr',
          'table', 'thead', 'tbody', 'tr', 'th', 'td',
          'div', 'span', 'input'
        ],
        ALLOWED_ATTR: [
          'href', 'title', 'target', 'rel', 'src', 'alt', 'loading',
          'class', 'style', 'disabled', 'checked', 'start', 'align'
        ]
      });
    } else {
      // Fallback sanitization
      const temp = document.createElement('div');
      temp.innerHTML = raw;
      // Remove dangerous elements
      temp.querySelectorAll('script, style, iframe, object, embed, form, input:not([type="checkbox"])').forEach((el) => el.remove());
      // Remove inline event handlers
      temp.querySelectorAll('[onclick],[onerror],[onload],[onmouseover],[onmouseenter],[onmouseleave]').forEach((el) => {
        [...el.attributes].forEach((attr) => {
          if (attr.name.startsWith('on')) el.removeAttribute(attr.name);
        });
      });
      temp.querySelectorAll('a[href^="javascript:"]').forEach((el) => el.removeAttribute('href'));
      safeHtml = temp.innerHTML;
    }

    return safeHtml;
  } catch (e) {
    console.warn('Markdown parse error:', e);
    // Fallback: escaped text with line breaks
    return escapeHtml(markdown || '').replace(/\n/g, '<br>');
  }
}

/**
 * Apply syntax highlighting and code block enhancements to a container.
 * @param {HTMLElement} container - Container element with rendered markdown
 * @returns {Promise<void>}
 */
export async function enhanceCodeBlocks(container) {
  checkLibraries();
  if (!_hljs) return;

  const codeBlocks = container.querySelectorAll('pre code:not([data-highlighted])');

  for (const codeEl of codeBlocks) {
    try {
      // Mark as processed to avoid double-enhancement
      codeEl.setAttribute('data-highlighted', 'true');

      // Apply syntax highlighting
      _hljs.highlightElement(codeEl);
    } catch (e) {
      // Unknown language, leave unhighlighted
    }

    // Wrap code block with header and copy button (only once)
    const pre = codeEl.parentElement;
    if (!pre || pre.classList.contains('code-block')) continue;
    if (pre.parentElement?.classList.contains('code-block')) continue;

    const langMatch = /language-(\w+)/.exec(codeEl.className || '');
    const lang = langMatch ? langMatch[1] : 'text';

    const block = document.createElement('div');
    block.className = 'code-block';
    block.innerHTML = `
      <div class="code-block-header">
        <span>${escapeHtml(lang)}</span>
        <button class="copy-code-btn" title="Copy code" aria-label="Copy code">
          <i class="fa-regular fa-copy"></i><span>Copy</span>
        </button>
      </div>
    `;

    pre.replaceWith(block);
    block.appendChild(pre);

    // Copy button handler
    const copyBtn = block.querySelector('.copy-code-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        const codeText = codeEl.textContent;

        try {
          await navigator.clipboard.writeText(codeText);
          btn.classList.add('copied');
          btn.innerHTML = `<i class="fa-solid fa-check"></i><span>Copied</span>`;
          setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = `<i class="fa-regular fa-copy"></i><span>Copy</span>`;
          }, 1600);
        } catch {
          // Fallback: select text
          const range = document.createRange();
          range.selectNodeContents(codeEl);
          const sel = window.getSelection();
          sel?.removeAllRanges();
          sel?.addRange(range);
        }
      });
    }
  }
}

/**
 * Render markdown to a DOM element with syntax highlighting.
 * @param {string} markdown - Markdown text
 * @returns {Promise<HTMLElement>} - Wrapper element with rendered content
 */
export async function renderMarkdownToElement(markdown) {
  const html = parseMarkdown(markdown);
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  await enhanceCodeBlocks(wrapper);
  return wrapper;
}

/**
 * Render markdown to HTML string (for message rendering).
 * This is the FINAL RENDER PASS - applies full markdown + enhancements.
 * @param {string} markdown - Markdown text
 * @returns {string} - HTML string
 */
export function renderMarkdown(markdown) {
  const temp = document.createElement('div');
  temp.innerHTML = parseMarkdown(markdown);

  // Apply syntax highlighting and code block wrapping synchronously
  checkLibraries();
  if (_hljs) {
    // Find all code blocks and process them
    temp.querySelectorAll('pre code').forEach((codeEl) => {
      // Skip if already enhanced
      if (codeEl.hasAttribute('data-highlighted')) return;

      try {
        codeEl.setAttribute('data-highlighted', 'true');
        _hljs.highlightElement(codeEl);
      } catch {
        // ignore
      }

      const pre = codeEl.parentElement;
      if (pre && !pre.classList.contains('code-block') && !pre.parentElement?.classList.contains('code-block')) {
        const langMatch = /language-(\w+)/.exec(codeEl.className || '');
        const lang = langMatch ? langMatch[1] : 'text';

        const block = document.createElement('div');
        block.className = 'code-block';
        block.innerHTML = `
          <div class="code-block-header">
            <span>${escapeHtml(lang)}</span>
            <button class="copy-code-btn"><i class="fa-regular fa-copy"></i><span>Copy</span></button>
          </div>
        `;
        pre.replaceWith(block);
        block.appendChild(pre);
      }
    });
  }

  return temp.innerHTML;
}

/**
 * Render markdown for STREAMING - produces visually stable output during incremental updates.
 * Uses marked.js 15+ parse with fallback to safe escaped rendering on parse errors.
 * Does NOT apply syntax highlighting during streaming (done in final pass).
 * @param {string} markdown - Accumulated markdown text so far
 * @returns {string} - HTML string safe for streaming display
 */
export function renderMarkdownStream(markdown) {
  checkLibraries();
  configureMarked();

  if (!_marked?.parse) {
    // Fallback: escaped text with line breaks
    return escapeHtml(markdown || '').replace(/\n/g, '<br>');
  }

  try {
    // Parse with marked - marked 15 handles incomplete markdown reasonably
    const raw = _marked.parse(markdown || '');

    // Sanitize but allow basic markdown elements
    let safeHtml = raw;
    if (_DOMPurify?.sanitize) {
      safeHtml = _DOMPurify.sanitize(raw, {
        USE_PROFILES: { html: true },
        ALLOWED_TAGS: [
          'p', 'br', 'strong', 'em', 'del', 'code', 'pre', 'blockquote',
          'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
          'ul', 'ol', 'li', 'a', 'hr',
          'div', 'span', 'input'
        ],
        ALLOWED_ATTR: [
          'href', 'title', 'target', 'rel', 'class', 'style',
          'disabled', 'checked', 'start', 'align'
        ]
      });
    } else {
      const temp = document.createElement('div');
      temp.innerHTML = raw;
      temp.querySelectorAll('script, style, iframe, object, embed, form, input:not([type="checkbox"])').forEach((el) => el.remove());
      temp.querySelectorAll('[onclick],[onerror],[onload],[onmouseover],[onmouseenter],[onmouseleave]').forEach((el) => {
        [...el.attributes].forEach((attr) => {
          if (attr.name.startsWith('on')) el.removeAttribute(attr.name);
        });
      });
      temp.querySelectorAll('a[href^="javascript:"]').forEach((el) => el.removeAttribute('href'));
      safeHtml = temp.innerHTML;
    }

    return safeHtml;
  } catch (e) {
    // On parse error (incomplete markdown), fallback to safe escaped rendering
    return escapeHtml(markdown || '').replace(/\n/g, '<br>');
  }
}

/**
 * Set code theme dynamically.
 * @param {string} theme - Theme name (e.g., 'github-dark', 'atom-one-dark')
 */
export function setCodeTheme(theme) {
  const themeEl = document.getElementById('hljs-theme');
  const urls = {
    'github-dark': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.0/styles/github-dark.min.css',
    'atom-one-dark': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.0/styles/atom-one-dark.min.css',
    'nord': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.0/styles/nord.min.css',
    'dracula': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.0/styles/dracula.min.css',
    'github': 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.0/styles/github.min.css',
  };

  if (themeEl && urls[theme]) {
    themeEl.href = urls[theme];
    document.body.setAttribute('data-code-theme', theme);
  }
}

/**
 * Check if markdown libraries are available.
 */
export function areMarkdownLibsLoaded() {
  checkLibraries();
  return !!_marked && !!_hljs;
}

/**
 * Final render pass for completed messages.
 * Re-renders the complete markdown with full enhancements.
 * @param {HTMLElement} messageNode - The assistant message DOM node
 * @param {string} markdown - Complete markdown source
 * @returns {Promise<void>}
 */
export async function finalizeMarkdownRender(messageNode, markdown) {
  const contentEl = messageNode.querySelector('.msg-content');
  if (!contentEl) return;

  try {
    // Full render with all enhancements
    const html = renderMarkdown(markdown);
    contentEl.innerHTML = html;

    // Apply async enhancements (highlighting is sync in renderMarkdown,
    // but we keep this for future async enhancements)
    await enhanceCodeBlocks(contentEl);
  } catch (e) {
    console.warn('Final markdown render error:', e);
    // Leave existing content on error
  }
}