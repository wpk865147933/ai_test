import type { Command, Response } from './types.js';
import type { BrowserManager } from './browser.js';

/**
 * A registered command handler.
 *
 * `action`   – the action string that triggers this handler (e.g. 'navigate')
 * `category` – the action-policy category (mirrors ACTION_CATEGORIES in action-policy.ts)
 * `handler`  – async function that executes the command
 */
export interface CommandHandler {
  action: string;
  category: string;
  handler: (command: Command, browser: BrowserManager) => Promise<Response>;
}

const registry = new Map<string, CommandHandler>();

/**
 * Register a command handler. Overwrites any previous handler for the same action.
 */
export function registerCommand(cmd: CommandHandler): void {
  registry.set(cmd.action, cmd);
}

/**
 * Look up a handler by action name. Returns undefined if not registered.
 */
export function getHandler(action: string): CommandHandler | undefined {
  return registry.get(action);
}

/**
 * Return all registered action names (sorted for determinism).
 */
export function listCommands(): string[] {
  return Array.from(registry.keys()).sort();
}

/**
 * Remove all registered handlers (useful for testing).
 */
export function clearRegistry(): void {
  registry.clear();
}
