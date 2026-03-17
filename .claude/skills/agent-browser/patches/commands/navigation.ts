import type { NavigateCommand, Command, Response } from '../types.js';
import type { BrowserManager } from '../browser.js';
import { successResponse } from '../protocol.js';
import { registerCommand } from '../command-registry.js';

// ---------- Individual handlers ----------

interface NavigateData {
  url: string;
  title: string;
}

async function handleNavigate(
  command: NavigateCommand,
  browser: BrowserManager
): Promise<Response<NavigateData>> {
  browser.checkDomainAllowed(command.url);

  const page = browser.getPage();

  // If headers are provided, set up scoped headers for this origin
  if (command.headers && Object.keys(command.headers).length > 0) {
    await browser.setScopedHeaders(command.url, command.headers);
  }

  await page.goto(command.url, {
    waitUntil: command.waitUntil ?? 'load',
  });

  return successResponse(command.id, {
    url: page.url(),
    title: await page.title(),
  });
}

async function handleBack(
  command: Command & { action: 'back' },
  browser: BrowserManager
): Promise<Response> {
  const page = browser.getPage();
  await page.goBack();
  return successResponse(command.id, { url: page.url() });
}

async function handleForward(
  command: Command & { action: 'forward' },
  browser: BrowserManager
): Promise<Response> {
  const page = browser.getPage();
  await page.goForward();
  return successResponse(command.id, { url: page.url() });
}

async function handleReload(
  command: Command & { action: 'reload' },
  browser: BrowserManager
): Promise<Response> {
  const page = browser.getPage();
  await page.reload();
  return successResponse(command.id, { url: page.url() });
}

async function handleUrl(
  command: Command & { action: 'url' },
  browser: BrowserManager
): Promise<Response> {
  const page = browser.getPage();
  return successResponse(command.id, { url: page.url() });
}

async function handleTitle(
  command: Command & { action: 'title' },
  browser: BrowserManager
): Promise<Response> {
  const page = browser.getPage();
  const title = await page.title();
  return successResponse(command.id, { title });
}

// ---------- Register all navigation commands ----------

export function registerNavigationCommands(): void {
  registerCommand({
    action: 'navigate',
    category: 'navigate',
    handler: (cmd, browser) => handleNavigate(cmd as NavigateCommand, browser),
  });
  registerCommand({
    action: 'back',
    category: 'navigate',
    handler: (cmd, browser) => handleBack(cmd as Command & { action: 'back' }, browser),
  });
  registerCommand({
    action: 'forward',
    category: 'navigate',
    handler: (cmd, browser) => handleForward(cmd as Command & { action: 'forward' }, browser),
  });
  registerCommand({
    action: 'reload',
    category: 'navigate',
    handler: (cmd, browser) => handleReload(cmd as Command & { action: 'reload' }, browser),
  });
  registerCommand({
    action: 'url',
    category: 'get',
    handler: (cmd, browser) => handleUrl(cmd as Command & { action: 'url' }, browser),
  });
  registerCommand({
    action: 'title',
    category: 'get',
    handler: (cmd, browser) => handleTitle(cmd as Command & { action: 'title' }, browser),
  });
}
