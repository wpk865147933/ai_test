import type {
  Command,
  Response,
  GetAttributeCommand,
  GetTextCommand,
  IsVisibleCommand,
  IsEnabledCommand,
  CountCommand,
} from '../types.js';
import type { BrowserManager } from '../browser.js';
import { successResponse } from '../protocol.js';
import { wrapWithBoundary } from '../snapshot.js';
import { registerCommand } from '../command-registry.js';

// ---------- Local helper (mirrors the one in actions.ts) ----------

function shouldWrapBoundary(command?: { noBoundary?: boolean }): boolean {
  if (command?.noBoundary) return false;
  if (process.env.AGENT_BROWSER_NO_BOUNDARY === '1') return false;
  return true;
}

// ---------- Individual handlers ----------

async function handleGetText(
  command: GetTextCommand & { noBoundary?: boolean },
  browser: BrowserManager
): Promise<Response> {
  const page = browser.getPage();
  const locator = browser.getLocator(command.selector);
  const inner = await locator.innerText();
  const text = inner || (await locator.textContent()) || '';
  return successResponse(command.id, {
    text: shouldWrapBoundary(command) ? wrapWithBoundary(text) : text,
    origin: page.url(),
  });
}

async function handleGetAttribute(
  command: GetAttributeCommand,
  browser: BrowserManager
): Promise<Response> {
  const page = browser.getPage();
  const locator = browser.getLocator(command.selector);
  const value = await locator.getAttribute(command.attribute);
  return successResponse(command.id, { attribute: command.attribute, value, origin: page.url() });
}

async function handleIsVisible(
  command: IsVisibleCommand,
  browser: BrowserManager
): Promise<Response> {
  const locator = browser.getLocator(command.selector);
  const visible = await locator.isVisible();
  return successResponse(command.id, { visible });
}

async function handleIsEnabled(
  command: IsEnabledCommand,
  browser: BrowserManager
): Promise<Response> {
  const locator = browser.getLocator(command.selector);
  const enabled = await locator.isEnabled();
  return successResponse(command.id, { enabled });
}

async function handleCount(
  command: CountCommand,
  browser: BrowserManager
): Promise<Response> {
  const page = browser.getPage();
  const count = await page.locator(command.selector).count();
  return successResponse(command.id, { count });
}

// ---------- Register all query commands ----------

export function registerQueryCommands(): void {
  registerCommand({
    action: 'gettext',
    category: 'get',
    handler: (cmd, browser) => handleGetText(cmd as GetTextCommand & { noBoundary?: boolean }, browser),
  });
  registerCommand({
    action: 'getattribute',
    category: 'get',
    handler: (cmd, browser) => handleGetAttribute(cmd as GetAttributeCommand, browser),
  });
  registerCommand({
    action: 'isvisible',
    category: 'get',
    handler: (cmd, browser) => handleIsVisible(cmd as IsVisibleCommand, browser),
  });
  registerCommand({
    action: 'isenabled',
    category: 'get',
    handler: (cmd, browser) => handleIsEnabled(cmd as IsEnabledCommand, browser),
  });
  registerCommand({
    action: 'count',
    category: 'get',
    handler: (cmd, browser) => handleCount(cmd as CountCommand, browser),
  });
}
