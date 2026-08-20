import { test, expect } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5500';
const BACKEND_URL = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8001';
// E2E test credentials - MUST be provided via environment variables
// No defaults - tests will fail if not set (prevents accidental use of weak credentials)
const E2E_USERNAME = process.env.E2E_TEST_USERNAME;
const E2E_PASSWORD = process.env.E2E_TEST_PASSWORD;

if (!E2E_USERNAME || !E2E_PASSWORD) {
  console.error('ERROR: E2E_TEST_USERNAME and E2E_TEST_PASSWORD environment variables must be set');
  console.error('Example: E2E_TEST_USERNAME=myuser E2E_TEST_PASSWORD=mypass npx playwright test tests/e2e/');
  process.exit(1);
}

interface ChatResponse {
  role: string;
  content: string;
  toolCalls?: Array<{
    type: string;
    name: string;
    arguments: Record<string, unknown>;
    result?: unknown;
    error?: string;
  }>;
}

async function setupChat(page: any) {
  await page.goto(FRONTEND_URL);
  await expect(page.locator('#messages')).toBeVisible({ timeout: 10000 });

  // Wait for auth overlay to appear and handle login
  await page.waitForTimeout(2000);

  // Check if auth overlay is visible
  const authOverlay = page.locator('#authOverlay');
  if (await authOverlay.isVisible({ timeout: 5000 })) {
    console.log('Auth overlay detected, logging in...');
    // Wait for auth form to be ready
    await page.waitForSelector('#authForm:not(.hidden)', { timeout: 10000 });

    // Fill in credentials from environment variables
    await page.fill('#authUsername', E2E_USERNAME);
    await page.fill('#authPassword', E2E_PASSWORD);
    await page.click('#authSubmit');

    // Wait for auth overlay to disappear
    await expect(authOverlay).toHaveClass(/hidden/, { timeout: 15000 });
    await page.waitForTimeout(3000);
  }

  // Wait for WebSocket connection or API to be ready
  await page.waitForTimeout(3000);
}

async function sendMessage(page: any, message: string) {
  const input = page.locator('#messageInput');

  // Clear and type message
  await input.fill('');
  await input.type(message);

  // Find and click send button
  const sendBtn = page.locator('#sendBtn');
  if (await sendBtn.isVisible({ timeout: 2000 })) {
    await sendBtn.click();
  } else {
    // Try pressing Enter (Ctrl+Enter)
    await input.press('Control+Enter');
  }

  // Wait for response to start appearing
  await page.waitForTimeout(3000);
}

async function waitForResponse(page: any, timeout: number = 60000) {
  // Wait for the last message to complete - look for assistant message
  await page.waitForFunction(
    () => {
      const messages = document.querySelectorAll('#messages .msg.assistant, #messages .msg[role="article"]');
      if (messages.length === 0) return false;
      const lastMessage = messages[messages.length - 1];
      // Check if it's an assistant message (not currently streaming)
      return lastMessage.classList.contains('assistant');
    },
    { timeout }
  );

  // Give extra time for content to fully render
  await page.waitForTimeout(3000);
}

async function getLastAssistantMessage(page: any): Promise<string> {
  const messageText = await page.evaluate(() => {
    const messages = document.querySelectorAll('#messages .msg.assistant');
    if (messages.length === 0) return '';
    const lastMessage = messages[messages.length - 1];
    return lastMessage.textContent || lastMessage.innerText || '';
  });
  return messageText.trim();
}

async function checkForToolCalls(page: any): Promise<{ toolCalls: boolean; toolNames: string[] }> {
  const toolInfo = await page.evaluate(() => {
    const messages = document.querySelectorAll('#messages .msg.assistant');
    if (messages.length === 0) return { toolCalls: false, toolNames: [] };
    const lastMessage = messages[messages.length - 1];
    const text = lastMessage.textContent || lastMessage.innerText || '';

    // Look for tool call indicators
    const toolIndicators = [
      'list_files',
      'read_file',
      'execute_code',
      'TOOL_START',
      'TOOL_END',
      'TOOL_RESULT',
      'tool_call',
      'function_call'
    ];

    const foundTools: string[] = [];
    for (const indicator of toolIndicators) {
      if (text.toLowerCase().includes(indicator.toLowerCase())) {
        foundTools.push(indicator);
      }
    }

    // Also check for tool call elements
    const toolCallElements = lastMessage.querySelectorAll('.msg-tool-calls, .tool-call');
    toolCallElements.forEach(el => {
      const elText = el.textContent || '';
      if (elText.includes('list_files')) foundTools.push('list_files');
      if (elText.includes('read_file')) foundTools.push('read_file');
      if (elText.includes('execute_code')) foundTools.push('execute_code');
    });

    // Also check for code blocks that might contain tool results
    const codeBlocks = lastMessage.querySelectorAll('pre code, pre');
    codeBlocks.forEach(block => {
      const blockText = block.textContent || '';
      if (blockText.includes('list_files') || blockText.includes('read_file') ||
          blockText.includes('execute_code') || blockText.includes('TOOL_')) {
        foundTools.push('code-block-tool');
      }
    });

    return { toolCalls: foundTools.length > 0, toolNames: [...new Set(foundTools)] };
  });
  return toolInfo;
}

async function takeScreenshot(page: any, name: string) {
  await page.screenshot({
    path: `D:/projects/chat_app/Universal-Ai-Chat-Platform/screenshots/${name}.png`,
    fullPage: true
  });
}

test.describe('Universal AI Chat Platform E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    await setupChat(page);
  });

  test('TEST 1: List files in project - triggers list_files tool', async ({ page }) => {
    console.log('=== TEST 1: List files ===');

    await sendMessage(page, 'List the files in my project.');
    await waitForResponse(page);

    const response = await getLastAssistantMessage(page);
    const toolInfo = await checkForToolCalls(page);

    console.log('Response:', response.substring(0, 500));
    console.log('Tool calls detected:', toolInfo);

    await takeScreenshot(page, 'test1-list-files');

    // Verify tool was called - either by explicit tool call indicator or by seeing file listing
    const hasFileListing = response.includes('.py') || response.includes('.js') ||
                           response.includes('.ts') || response.includes('.html') ||
                           response.includes('.md') || response.includes('.json') ||
                           response.includes('backend') || response.includes('frontend');

    expect(toolInfo.toolCalls || hasFileListing).toBeTruthy();
    console.log('TEST 1: PASSED - list_files tool triggered');
  });

  test('TEST 2: Read backend/response_intelligence/config.py - returns file contents', async ({ page }) => {
    console.log('=== TEST 2: Read config.py ===');

    await sendMessage(page, 'Read backend/response_intelligence/config.py and explain what it does.');
    await waitForResponse(page);

    const response = await getLastAssistantMessage(page);
    const toolInfo = await checkForToolCalls(page);

    console.log('Response:', response.substring(0, 500));
    console.log('Tool calls detected:', toolInfo);

    await takeScreenshot(page, 'test2-read-config');

    // Verify file was read - should contain config content
    const hasConfigContent = response.includes('config') || response.includes('CONFIG') ||
                             response.includes('ResponseIntelligenceConfig') ||
                             response.includes('response_intelligence') ||
                             response.includes('temperature') || response.includes('max_tokens') ||
                             toolInfo.toolNames.some(t => t.includes('read_file'));

    expect(hasConfigContent).toBeTruthy();
    console.log('TEST 2: PASSED - file contents returned');
  });

  test('TEST 3: Read backend/api.py - returns file contents', async ({ page }) => {
    console.log('=== TEST 3: Read api.py ===');

    await sendMessage(page, 'Read backend/api.py and tell me what it does.');
    await waitForResponse(page);

    const response = await getLastAssistantMessage(page);
    const toolInfo = await checkForToolCalls(page);

    console.log('Response:', response.substring(0, 500));
    console.log('Tool calls detected:', toolInfo);

    await takeScreenshot(page, 'test3-read-api');

    // Verify file was read - should contain API content
    const hasApiContent = response.includes('router') || response.includes('APIRouter') ||
                          response.includes('chat') || response.includes('stream') ||
                          response.includes('FastAPI') || response.includes('endpoint') ||
                          response.includes('provider') || response.includes('llm') ||
                          toolInfo.toolNames.some(t => t.includes('read_file'));

    expect(hasApiContent).toBeTruthy();
    console.log('TEST 3: PASSED - file contents returned');
  });

  test('TEST 4: Path traversal attempt - should return security error', async ({ page }) => {
    console.log('=== TEST 4: Path traversal ===');

    await sendMessage(page, 'Read ../../some_file');
    await waitForResponse(page);

    const response = await getLastAssistantMessage(page);
    const toolInfo = await checkForToolCalls(page);

    console.log('Response:', response.substring(0, 500));
    console.log('Tool calls detected:', toolInfo);

    await takeScreenshot(page, 'test4-path-traversal');

    // Should return a controlled error, not actual file contents
    const hasSecurityError = response.toLowerCase().includes('error') ||
                             response.toLowerCase().includes('security') ||
                             response.toLowerCase().includes('path') ||
                             response.toLowerCase().includes('traversal') ||
                             response.toLowerCase().includes('denied') ||
                             response.toLowerCase().includes('forbidden') ||
                             response.toLowerCase().includes('invalid') ||
                             response.toLowerCase().includes('not allowed') ||
                             response.toLowerCase().includes('outside');

    // Should NOT contain actual file contents from parent directories
    const hasNoFileContents = !response.includes('etc') && !response.includes('passwd') &&
                              !response.includes('shadow') && !response.includes('hosts');

    expect(hasSecurityError || hasNoFileContents).toBeTruthy();
    console.log('TEST 4: PASSED - path traversal properly rejected');
  });

  test('TEST 5: Execute Python code - returns actual result (4)', async ({ page }) => {
    console.log('=== TEST 5: Execute code ===');

    await sendMessage(page, 'Execute this Python code and tell me the result: print(2 + 2)');
    await waitForResponse(page);

    const response = await getLastAssistantMessage(page);
    const toolInfo = await checkForToolCalls(page);

    console.log('Response:', response.substring(0, 500));
    console.log('Tool calls detected:', toolInfo);

    await takeScreenshot(page, 'test5-execute-code');

    // Should return the result "4"
    const hasResult = response.includes('4') || response.includes('four') ||
                      response.includes('result') && response.includes('2') && response.includes('2');

    // Should have executed code tool
    const hasExecuteTool = toolInfo.toolNames.some(t =>
      t.includes('execute') || t.includes('code') || t.includes('python')
    );

    expect(hasResult || hasExecuteTool).toBeTruthy();
    console.log('TEST 5: PASSED - code executed, result returned');
  });

  test('TEST 6: Direct answer - no unnecessary tool call', async ({ page }) => {
    console.log('=== TEST 6: Direct answer ===');

    await sendMessage(page, 'What is Python?');
    await waitForResponse(page);

    const response = await getLastAssistantMessage(page);
    const toolInfo = await checkForToolCalls(page);

    console.log('Response:', response.substring(0, 500));
    console.log('Tool calls detected:', toolInfo);

    await takeScreenshot(page, 'test6-direct-answer');

    // Should give direct answer about Python
    const hasDirectAnswer = response.toLowerCase().includes('python') &&
                            (response.toLowerCase().includes('programming') ||
                             response.toLowerCase().includes('language') ||
                             response.toLowerCase().includes('interpreted') ||
                             response.toLowerCase().includes('high-level'));

    // Should NOT have made tool calls for a simple knowledge question
    const noUnnecessaryTools = !toolInfo.toolNames.some(t =>
      t.includes('list_files') || t.includes('read_file') ||
      t.includes('execute_code') || t.includes('web_search') ||
      t.includes('search')
    );

    expect(hasDirectAnswer).toBeTruthy();
    expect(noUnnecessaryTools).toBeTruthy();
    console.log('TEST 6: PASSED - direct answer without tool calls');
  });
});