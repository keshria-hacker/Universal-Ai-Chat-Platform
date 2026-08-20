# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tests\e2e\e2e_tests.spec.ts >> Universal AI Chat Platform E2E Tests >> TEST 5: Execute Python code - returns actual result (4)
- Location: tests\e2e\e2e_tests.spec.ts:273:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5500/
Call log:
  - navigating to "http://127.0.0.1:5500/", waiting until "load"

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | const FRONTEND_URL = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5500';
  4   | const BACKEND_URL = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8001';
  5   | // E2E test credentials - MUST be provided via environment variables
  6   | // No defaults - tests will fail if not set (prevents accidental use of weak credentials)
  7   | const E2E_USERNAME = process.env.E2E_TEST_USERNAME;
  8   | const E2E_PASSWORD = process.env.E2E_TEST_PASSWORD;
  9   | 
  10  | if (!E2E_USERNAME || !E2E_PASSWORD) {
  11  |   console.error('ERROR: E2E_TEST_USERNAME and E2E_TEST_PASSWORD environment variables must be set');
  12  |   console.error('Example: E2E_TEST_USERNAME=myuser E2E_TEST_PASSWORD=mypass npx playwright test tests/e2e/');
  13  |   process.exit(1);
  14  | }
  15  | 
  16  | interface ChatResponse {
  17  |   role: string;
  18  |   content: string;
  19  |   toolCalls?: Array<{
  20  |     type: string;
  21  |     name: string;
  22  |     arguments: Record<string, unknown>;
  23  |     result?: unknown;
  24  |     error?: string;
  25  |   }>;
  26  | }
  27  | 
  28  | async function setupChat(page: any) {
> 29  |   await page.goto(FRONTEND_URL);
      |              ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5500/
  30  |   await expect(page.locator('#messages')).toBeVisible({ timeout: 10000 });
  31  | 
  32  |   // Wait for auth overlay to appear and handle login
  33  |   await page.waitForTimeout(2000);
  34  | 
  35  |   // Check if auth overlay is visible
  36  |   const authOverlay = page.locator('#authOverlay');
  37  |   if (await authOverlay.isVisible({ timeout: 5000 })) {
  38  |     console.log('Auth overlay detected, logging in...');
  39  |     // Wait for auth form to be ready
  40  |     await page.waitForSelector('#authForm:not(.hidden)', { timeout: 10000 });
  41  | 
  42  |     // Fill in credentials from environment variables
  43  |     await page.fill('#authUsername', E2E_USERNAME);
  44  |     await page.fill('#authPassword', E2E_PASSWORD);
  45  |     await page.click('#authSubmit');
  46  | 
  47  |     // Wait for auth overlay to disappear
  48  |     await expect(authOverlay).toHaveClass(/hidden/, { timeout: 15000 });
  49  |     await page.waitForTimeout(3000);
  50  |   }
  51  | 
  52  |   // Wait for WebSocket connection or API to be ready
  53  |   await page.waitForTimeout(3000);
  54  | }
  55  | 
  56  | async function sendMessage(page: any, message: string) {
  57  |   const input = page.locator('#messageInput');
  58  | 
  59  |   // Clear and type message
  60  |   await input.fill('');
  61  |   await input.type(message);
  62  | 
  63  |   // Find and click send button
  64  |   const sendBtn = page.locator('#sendBtn');
  65  |   if (await sendBtn.isVisible({ timeout: 2000 })) {
  66  |     await sendBtn.click();
  67  |   } else {
  68  |     // Try pressing Enter (Ctrl+Enter)
  69  |     await input.press('Control+Enter');
  70  |   }
  71  | 
  72  |   // Wait for response to start appearing
  73  |   await page.waitForTimeout(3000);
  74  | }
  75  | 
  76  | async function waitForResponse(page: any, timeout: number = 60000) {
  77  |   // Wait for the last message to complete - look for assistant message
  78  |   await page.waitForFunction(
  79  |     () => {
  80  |       const messages = document.querySelectorAll('#messages .msg.assistant, #messages .msg[role="article"]');
  81  |       if (messages.length === 0) return false;
  82  |       const lastMessage = messages[messages.length - 1];
  83  |       // Check if it's an assistant message (not currently streaming)
  84  |       return lastMessage.classList.contains('assistant');
  85  |     },
  86  |     { timeout }
  87  |   );
  88  | 
  89  |   // Give extra time for content to fully render
  90  |   await page.waitForTimeout(3000);
  91  | }
  92  | 
  93  | async function getLastAssistantMessage(page: any): Promise<string> {
  94  |   const messageText = await page.evaluate(() => {
  95  |     const messages = document.querySelectorAll('#messages .msg.assistant');
  96  |     if (messages.length === 0) return '';
  97  |     const lastMessage = messages[messages.length - 1];
  98  |     return lastMessage.textContent || lastMessage.innerText || '';
  99  |   });
  100 |   return messageText.trim();
  101 | }
  102 | 
  103 | async function checkForToolCalls(page: any): Promise<{ toolCalls: boolean; toolNames: string[] }> {
  104 |   const toolInfo = await page.evaluate(() => {
  105 |     const messages = document.querySelectorAll('#messages .msg.assistant');
  106 |     if (messages.length === 0) return { toolCalls: false, toolNames: [] };
  107 |     const lastMessage = messages[messages.length - 1];
  108 |     const text = lastMessage.textContent || lastMessage.innerText || '';
  109 | 
  110 |     // Look for tool call indicators
  111 |     const toolIndicators = [
  112 |       'list_files',
  113 |       'read_file',
  114 |       'execute_code',
  115 |       'TOOL_START',
  116 |       'TOOL_END',
  117 |       'TOOL_RESULT',
  118 |       'tool_call',
  119 |       'function_call'
  120 |     ];
  121 | 
  122 |     const foundTools: string[] = [];
  123 |     for (const indicator of toolIndicators) {
  124 |       if (text.toLowerCase().includes(indicator.toLowerCase())) {
  125 |         foundTools.push(indicator);
  126 |       }
  127 |     }
  128 | 
  129 |     // Also check for tool call elements
```