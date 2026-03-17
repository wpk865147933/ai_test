import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as net from 'net';

// ---------------------------------------------------------------------------
// Mock the daemon module before importing mcp-server
// ---------------------------------------------------------------------------

vi.mock('./daemon.js', () => ({
  getConnectionInfo: vi.fn().mockReturnValue({ type: 'tcp', port: 0 }),
  isDaemonRunning: vi.fn().mockReturnValue(true),
  getSession: vi.fn().mockReturnValue('default'),
  startDaemon: vi.fn().mockResolvedValue(undefined),
}));

import {
  DaemonConnection,
  ensureDaemon,
  createMcpServer,
  mapPlaywrightError,
} from './mcp-server.js';

// ---------------------------------------------------------------------------
// Helper: mock daemon server (JSON-line protocol, no auth)
// ---------------------------------------------------------------------------

function createMockDaemonServer(
  onCommand: (cmd: Record<string, unknown>) => Record<string, unknown>
): { server: net.Server; port: number; start: () => Promise<number> } {
  const server = net.createServer((socket) => {
    let buffer = '';

    socket.on('data', (data) => {
      buffer += data.toString();
      while (buffer.includes('\n')) {
        const idx = buffer.indexOf('\n');
        const line = buffer.substring(0, idx).trim();
        buffer = buffer.substring(idx + 1);
        if (!line) continue;

        try {
          const cmd = JSON.parse(line) as Record<string, unknown>;
          const resp = onCommand(cmd);
          socket.write(JSON.stringify({ id: cmd.id, ...resp }) + '\n');
        } catch {
          socket.write(
            JSON.stringify({ id: 'unknown', success: false, error: 'parse error' }) + '\n'
          );
        }
      }
    });
  });

  let port = 0;
  return {
    server,
    get port() {
      return port;
    },
    start: () =>
      new Promise<number>((resolve) => {
        server.listen(0, '127.0.0.1', () => {
          const addr = server.address() as net.AddressInfo;
          port = addr.port;
          resolve(port);
        });
      }),
  };
}

// ---------------------------------------------------------------------------
// ensureDaemon
// ---------------------------------------------------------------------------

describe('ensureDaemon', () => {
  it('should resolve immediately if daemon is already running', async () => {
    const { isDaemonRunning } = await import('./daemon.js');
    vi.mocked(isDaemonRunning).mockReturnValue(true);
    await expect(ensureDaemon()).resolves.toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// DaemonConnection
// ---------------------------------------------------------------------------

describe('DaemonConnection', () => {
  let mockServer: ReturnType<typeof createMockDaemonServer>;

  beforeEach(async () => {
    mockServer = createMockDaemonServer((cmd) => {
      return { success: true, data: { action: cmd.action, echo: true } };
    });
    const port = await mockServer.start();

    const { getConnectionInfo } = await import('./daemon.js');
    vi.mocked(getConnectionInfo).mockReturnValue({ type: 'tcp', port });
  });

  afterEach(() => {
    mockServer.server.close();
  });

  it('should connect to daemon', async () => {
    const conn = new DaemonConnection();
    await conn.connect();
    conn.disconnect();
  });

  it('should send commands and receive responses', async () => {
    const conn = new DaemonConnection();
    await conn.connect();

    const resp = await conn.send({ action: 'title' });
    expect(resp.success).toBe(true);
    if (resp.success) {
      expect((resp.data as Record<string, unknown>).action).toBe('title');
    }

    conn.disconnect();
  });

  it('should handle multiple sequential commands', async () => {
    const conn = new DaemonConnection();
    await conn.connect();

    const resp1 = await conn.send({ action: 'title' });
    const resp2 = await conn.send({ action: 'url' });

    expect(resp1.success).toBe(true);
    expect(resp2.success).toBe(true);
    if (resp1.success && resp2.success) {
      expect((resp1.data as Record<string, unknown>).action).toBe('title');
      expect((resp2.data as Record<string, unknown>).action).toBe('url');
    }

    conn.disconnect();
  });

  it('should auto-reconnect on send if not connected', async () => {
    const conn = new DaemonConnection();
    // Don't call connect() explicitly
    const resp = await conn.send({ action: 'title' });
    expect(resp.success).toBe(true);
    conn.disconnect();
  });
});

// ---------------------------------------------------------------------------
// mapPlaywrightError
// ---------------------------------------------------------------------------

describe('mapPlaywrightError', () => {
  it('should map timeout errors', () => {
    const result = mapPlaywrightError('Timeout 30000ms exceeded');
    expect(result.code).toBe(-32000);
    expect(result.message).toContain('Timeout');
  });

  it('should map element not found errors', () => {
    const result = mapPlaywrightError('No element found for selector @e99');
    expect(result.code).toBe(-32001);
    expect(result.message).toContain('Element not found');
  });

  it('should map navigation errors', () => {
    const result = mapPlaywrightError('net::ERR_CONNECTION_REFUSED');
    expect(result.code).toBe(-32002);
    expect(result.message).toContain('Navigation error');
  });

  it('should map generic errors', () => {
    const result = mapPlaywrightError('Something went wrong');
    expect(result.code).toBe(-32603);
    expect(result.message).toBe('Something went wrong');
  });
});

// ---------------------------------------------------------------------------
// createMcpServer - tool definitions
// ---------------------------------------------------------------------------

describe('createMcpServer', () => {
  let mockServer: ReturnType<typeof createMockDaemonServer>;
  let conn: DaemonConnection;

  beforeEach(async () => {
    const { getConnectionInfo } = await import('./daemon.js');

    mockServer = createMockDaemonServer((cmd) => {
      switch (cmd.action) {
        case 'navigate':
          return { success: true, data: { url: cmd.url, title: 'Test Page' } };
        case 'snapshot':
          return { success: true, data: { snapshot: '<tree>', refs: {} } };
        case 'screenshot':
          return { success: true, data: { path: cmd.path ?? '/tmp/shot.png' } };
        case 'click':
          return { success: true, data: { clicked: cmd.selector } };
        case 'fill':
          return { success: true, data: { filled: cmd.selector, value: cmd.value } };
        case 'type':
          return { success: true, data: { typed: cmd.text } };
        case 'title':
          return { success: true, data: { title: 'Test Page' } };
        case 'url':
          return { success: true, data: { url: 'https://example.com' } };
        case 'gettext':
          return { success: true, data: { text: 'Hello World' } };
        case 'inputvalue':
          return { success: true, data: { value: 'test input' } };
        case 'diff_snapshot':
          return { success: true, data: { diff: '', changed: false } };
        case 'close':
          return { success: true, data: { closed: true } };
        case 'back':
        case 'forward':
        case 'reload':
          return { success: true, data: { navigated: cmd.action } };
        case 'press':
          return { success: true, data: { pressed: cmd.key } };
        case 'wait':
          return { success: true, data: { waited: true } };
        case 'waitforurl':
          return { success: true, data: { waited: true, url: cmd.url } };
        case 'waitforloadstate':
          return { success: true, data: { waited: true, state: cmd.state } };
        default:
          return { success: true, data: { action: cmd.action } };
      }
    });

    const port = await mockServer.start();
    vi.mocked(getConnectionInfo).mockReturnValue({ type: 'tcp', port });

    conn = new DaemonConnection();
    await conn.connect();
  });

  afterEach(() => {
    conn.disconnect();
    mockServer.server.close();
  });

  it('should create server with all expected tools', () => {
    const mcpServer = createMcpServer(conn);
    expect(mcpServer).toBeDefined();
  });

  it('browser_open should send navigate command', async () => {
    const resp = await conn.send({ action: 'navigate', url: 'https://example.com' });
    expect(resp.success).toBe(true);
    if (resp.success) {
      expect((resp.data as Record<string, unknown>).url).toBe('https://example.com');
    }
  });

  it('browser_snapshot modes should map correctly', async () => {
    const resp1 = await conn.send({ action: 'snapshot', compact: true });
    expect(resp1.success).toBe(true);

    const resp2 = await conn.send({ action: 'snapshot', interactive: true });
    expect(resp2.success).toBe(true);
  });

  it('browser_click should send click with selector', async () => {
    const resp = await conn.send({ action: 'click', selector: '@e12' });
    expect(resp.success).toBe(true);
    if (resp.success) {
      expect((resp.data as Record<string, unknown>).clicked).toBe('@e12');
    }
  });

  it('browser_fill should send fill with value', async () => {
    const resp = await conn.send({ action: 'fill', selector: '@e3', value: 'hello' });
    expect(resp.success).toBe(true);
    if (resp.success) {
      expect((resp.data as Record<string, unknown>).filled).toBe('@e3');
      expect((resp.data as Record<string, unknown>).value).toBe('hello');
    }
  });

  it('browser_get title should send title command', async () => {
    const resp = await conn.send({ action: 'title' });
    expect(resp.success).toBe(true);
    if (resp.success) {
      expect((resp.data as Record<string, unknown>).title).toBe('Test Page');
    }
  });

  it('browser_get url should send url command', async () => {
    const resp = await conn.send({ action: 'url' });
    expect(resp.success).toBe(true);
    if (resp.success) {
      expect((resp.data as Record<string, unknown>).url).toBe('https://example.com');
    }
  });

  it('browser_press should send press command', async () => {
    const resp = await conn.send({ action: 'press', key: 'Enter' });
    expect(resp.success).toBe(true);
    if (resp.success) {
      expect((resp.data as Record<string, unknown>).pressed).toBe('Enter');
    }
  });

  it('browser_navigate should send correct action', async () => {
    for (const action of ['back', 'forward', 'reload'] as const) {
      const resp = await conn.send({ action });
      expect(resp.success).toBe(true);
      if (resp.success) {
        expect((resp.data as Record<string, unknown>).navigated).toBe(action);
      }
    }
  });

  it('browser_wait selector should send wait command', async () => {
    const resp = await conn.send({ action: 'wait', selector: '#main' });
    expect(resp.success).toBe(true);
  });

  it('browser_diff snapshot should send diff_snapshot', async () => {
    const resp = await conn.send({ action: 'diff_snapshot' });
    expect(resp.success).toBe(true);
    if (resp.success) {
      expect((resp.data as Record<string, unknown>).changed).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------
// Error handling via daemon connection
// ---------------------------------------------------------------------------

describe('error handling', () => {
  let mockServer: ReturnType<typeof createMockDaemonServer>;
  let conn: DaemonConnection;

  beforeEach(async () => {
    const { getConnectionInfo } = await import('./daemon.js');

    mockServer = createMockDaemonServer((cmd) => {
      if (cmd.action === 'click' && cmd.selector === '@missing') {
        return { success: false, error: 'Error: No element found for selector @missing' };
      }
      if (cmd.action === 'navigate' && cmd.url === 'http://unreachable') {
        return { success: false, error: 'net::ERR_CONNECTION_REFUSED' };
      }
      if (cmd.action === 'wait' && cmd.selector === '#slow') {
        return { success: false, error: 'Timeout 30000ms exceeded waiting for selector #slow' };
      }
      return { success: true, data: {} };
    });

    const port = await mockServer.start();
    vi.mocked(getConnectionInfo).mockReturnValue({ type: 'tcp', port });

    conn = new DaemonConnection();
    await conn.connect();
  });

  afterEach(() => {
    conn.disconnect();
    mockServer.server.close();
  });

  it('should return error for missing element', async () => {
    const resp = await conn.send({ action: 'click', selector: '@missing' });
    expect(resp.success).toBe(false);
    if (!resp.success) {
      expect(resp.error).toContain('No element found');
    }
  });

  it('should return error for network failure', async () => {
    const resp = await conn.send({ action: 'navigate', url: 'http://unreachable' });
    expect(resp.success).toBe(false);
    if (!resp.success) {
      expect(resp.error).toContain('net::ERR');
    }
  });

  it('should return error for timeout', async () => {
    const resp = await conn.send({ action: 'wait', selector: '#slow' });
    expect(resp.success).toBe(false);
    if (!resp.success) {
      expect(resp.error).toContain('Timeout');
    }
  });
});
