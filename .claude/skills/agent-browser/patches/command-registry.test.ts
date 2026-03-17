import { describe, it, expect, beforeEach } from 'vitest';
import {
  registerCommand,
  getHandler,
  listCommands,
  clearRegistry,
  type CommandHandler,
} from './command-registry.js';

describe('command-registry', () => {
  beforeEach(() => {
    clearRegistry();
  });

  it('registers and retrieves a command handler', async () => {
    const handler: CommandHandler = {
      action: 'test_action',
      category: 'navigate',
      handler: async (cmd: any) => ({ id: cmd.id, status: 'ok', data: { done: true } }),
    };
    registerCommand(handler);

    const retrieved = getHandler('test_action');
    expect(retrieved).toBeDefined();
    expect(retrieved!.action).toBe('test_action');
    expect(retrieved!.category).toBe('navigate');

    // Handler should be callable
    const result = await retrieved!.handler({ id: '1', action: 'test_action' } as any, {} as any);
    expect(result).toEqual({ id: '1', status: 'ok', data: { done: true } });
  });

  it('returns undefined for unknown action', () => {
    const handler = getHandler('nonexistent');
    expect(handler).toBeUndefined();
  });

  it('overwrites handler on duplicate register', () => {
    registerCommand({
      action: 'dup',
      category: 'get',
      handler: async () => ({ id: '1', status: 'ok', data: 'first' }),
    });
    registerCommand({
      action: 'dup',
      category: 'navigate',
      handler: async () => ({ id: '2', status: 'ok', data: 'second' }),
    });

    const h = getHandler('dup');
    expect(h!.category).toBe('navigate');
  });

  it('lists all registered command names sorted', () => {
    registerCommand({ action: 'zebra', category: 'get', handler: async () => ({} as any) });
    registerCommand({ action: 'alpha', category: 'get', handler: async () => ({} as any) });
    registerCommand({ action: 'middle', category: 'get', handler: async () => ({} as any) });

    expect(listCommands()).toEqual(['alpha', 'middle', 'zebra']);
  });

  it('clearRegistry removes all handlers', () => {
    registerCommand({ action: 'a', category: 'get', handler: async () => ({} as any) });
    registerCommand({ action: 'b', category: 'get', handler: async () => ({} as any) });
    expect(listCommands()).toHaveLength(2);

    clearRegistry();
    expect(listCommands()).toHaveLength(0);
    expect(getHandler('a')).toBeUndefined();
  });
});

describe('command-registry integration with commands/', () => {
  beforeEach(() => {
    clearRegistry();
  });

  it('registerNavigationCommands populates 6 navigation/get commands', async () => {
    const { registerNavigationCommands } = await import('./commands/navigation.js');
    registerNavigationCommands();

    const commands = listCommands();
    expect(commands).toContain('navigate');
    expect(commands).toContain('back');
    expect(commands).toContain('forward');
    expect(commands).toContain('reload');
    expect(commands).toContain('url');
    expect(commands).toContain('title');
    expect(commands).toHaveLength(6);

    // Verify categories
    expect(getHandler('navigate')!.category).toBe('navigate');
    expect(getHandler('back')!.category).toBe('navigate');
    expect(getHandler('url')!.category).toBe('get');
    expect(getHandler('title')!.category).toBe('get');
  });

  it('registerQueryCommands populates 5 query commands', async () => {
    const { registerQueryCommands } = await import('./commands/query.js');
    registerQueryCommands();

    const commands = listCommands();
    expect(commands).toContain('gettext');
    expect(commands).toContain('getattribute');
    expect(commands).toContain('isvisible');
    expect(commands).toContain('isenabled');
    expect(commands).toContain('count');
    expect(commands).toHaveLength(5);

    // All should be 'get' category
    for (const action of commands) {
      expect(getHandler(action)!.category).toBe('get');
    }
  });

  it('registerAllCommands populates all 11 commands', async () => {
    const { registerAllCommands } = await import('./commands/index.js');
    registerAllCommands();

    expect(listCommands()).toHaveLength(11);
  });

  it('dispatchAction uses registry for migrated commands and falls back for others', async () => {
    // This is a conceptual test: if we register a handler, getHandler returns it;
    // if not registered, getHandler returns undefined (fallback path)
    const { registerAllCommands } = await import('./commands/index.js');
    registerAllCommands();

    // Migrated command should be found
    expect(getHandler('navigate')).toBeDefined();
    expect(getHandler('gettext')).toBeDefined();

    // Non-migrated command should NOT be in registry
    expect(getHandler('click')).toBeUndefined();
    expect(getHandler('screenshot')).toBeUndefined();
    expect(getHandler('launch')).toBeUndefined();
  });
});
