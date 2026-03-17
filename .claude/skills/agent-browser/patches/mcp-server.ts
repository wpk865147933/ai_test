/**
 * MCP Server adapter for agent-browser.
 *
 * Exposes browser automation commands as MCP tools via stdio (default) or SSE transport.
 * Connects to the agent-browser daemon over its Unix socket (or TCP on Windows),
 * reusing the existing JSON-line protocol from daemon.ts.
 */

import * as net from 'net';
import { randomUUID } from 'crypto';
import { spawn } from 'child_process';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { z } from 'zod';

import {
  getConnectionInfo,
  isDaemonRunning,
  getSession,
  startDaemon,
} from './daemon.js';

import type { Response } from './types.js';

// ---------------------------------------------------------------------------
// Daemon connection helpers
// ---------------------------------------------------------------------------

/**
 * Ensure the daemon is running, starting it if necessary.
 * Uses the existing startDaemon helper (which writes pid files etc).
 * Falls back to spawning a new process if startDaemon is not suitable
 * for out-of-process startup.
 */
export async function ensureDaemon(session?: string): Promise<void> {
  if (isDaemonRunning(session)) return;

  // Spawn daemon in a detached child process
  const binPath = process.argv[1]; // agent-browser entry
  const daemonProcess = spawn(
    process.execPath,
    [binPath, 'daemon'],
    {
      detached: true,
      stdio: 'ignore',
      env: {
        ...process.env,
        ...(session ? { AGENT_BROWSER_SESSION: session } : {}),
      },
    }
  );
  daemonProcess.unref();

  // Wait for daemon to become ready (pid file + socket)
  const maxWait = 10_000;
  const interval = 200;
  let waited = 0;
  while (waited < maxWait) {
    await new Promise((r) => setTimeout(r, interval));
    waited += interval;
    if (isDaemonRunning(session)) return;
  }
  throw new Error('Timed out waiting for agent-browser daemon to start');
}

/**
 * Persistent connection to the agent-browser daemon.
 *
 * The daemon uses a simple JSON-line protocol (no auth handshake):
 *   Client sends: { "id": "...", "action": "...", ... }\n
 *   Daemon sends: { "id": "...", "success": true/false, ... }\n
 *
 * Responses are matched to requests by order (FIFO queue).
 */
export class DaemonConnection {
  private socket: net.Socket | null = null;
  private buffer = '';
  private responseQueue: Array<{
    resolve: (resp: Response) => void;
    reject: (err: Error) => void;
  }> = [];
  private connected = false;
  private session: string;

  constructor(session?: string) {
    this.session = session ?? getSession();
  }

  /** Connect to the daemon socket. */
  async connect(): Promise<void> {
    if (this.connected) return;

    await ensureDaemon(this.session);

    const connInfo = getConnectionInfo(this.session);

    return new Promise((resolve, reject) => {
      const socket =
        connInfo.type === 'unix'
          ? net.createConnection({ path: connInfo.path })
          : net.createConnection({ port: connInfo.port, host: '127.0.0.1' });

      socket.on('connect', () => {
        this.connected = true;
        this.socket = socket;
        resolve();
      });

      socket.on('data', (data) => {
        this.buffer += data.toString();

        // Process complete lines
        while (this.buffer.includes('\n')) {
          const idx = this.buffer.indexOf('\n');
          const line = this.buffer.substring(0, idx);
          this.buffer = this.buffer.substring(idx + 1);

          if (!line.trim()) continue;
          try {
            const resp = JSON.parse(line) as Response;
            const pending = this.responseQueue.shift();
            if (pending) pending.resolve(resp);
          } catch {
            // Malformed response — skip
          }
        }
      });

      socket.on('error', (err) => {
        this.connected = false;
        if (!this.socket) {
          // Connection phase
          reject(err);
        }
        // Reject all pending requests
        for (const pending of this.responseQueue) {
          pending.reject(err);
        }
        this.responseQueue = [];
      });

      socket.on('close', () => {
        this.connected = false;
        this.socket = null;
        for (const pending of this.responseQueue) {
          pending.reject(new Error('Daemon connection closed'));
        }
        this.responseQueue = [];
      });
    });
  }

  /** Send a command to the daemon and wait for the response. */
  async send(command: Record<string, unknown>): Promise<Response> {
    if (!this.connected || !this.socket) {
      await this.connect();
    }
    if (!this.socket) throw new Error('Not connected to daemon');

    const id = (command.id as string) ?? randomUUID();
    const payload = JSON.stringify({ ...command, id }) + '\n';

    return new Promise((resolve, reject) => {
      this.responseQueue.push({ resolve, reject });
      this.socket!.write(payload);
    });
  }

  /** Disconnect from daemon. */
  disconnect(): void {
    if (this.socket) {
      this.socket.destroy();
      this.socket = null;
    }
    this.connected = false;
    this.responseQueue = [];
  }
}

// ---------------------------------------------------------------------------
// Error mapping: Playwright errors → MCP error format
// ---------------------------------------------------------------------------

export function mapPlaywrightError(error: string): { code: number; message: string } {
  if (/timeout/i.test(error)) {
    return { code: -32000, message: `Timeout: ${error}` };
  }
  if (/no element/i.test(error) || /not found/i.test(error) || /could not find/i.test(error)) {
    return { code: -32001, message: `Element not found: ${error}` };
  }
  if (/net::ERR/i.test(error) || /navigation/i.test(error)) {
    return { code: -32002, message: `Navigation error: ${error}` };
  }
  return { code: -32603, message: error };
}

// ---------------------------------------------------------------------------
// MCP Tool result helpers
// ---------------------------------------------------------------------------

function toolResult(
  resp: Response
): { content: Array<{ type: 'text'; text: string }>; isError?: boolean } {
  if (resp.success) {
    const text =
      typeof resp.data === 'string'
        ? resp.data
        : JSON.stringify(resp.data, null, 2);
    return { content: [{ type: 'text' as const, text }] };
  }
  const mapped = mapPlaywrightError(resp.error ?? 'Unknown error');
  return {
    content: [{ type: 'text' as const, text: mapped.message }],
    isError: true,
  };
}

// ---------------------------------------------------------------------------
// Build MCP Server with tool definitions
// ---------------------------------------------------------------------------

export function createMcpServer(conn: DaemonConnection): McpServer {
  const server = new McpServer(
    { name: 'agent-browser', version: '0.18.0' },
    { capabilities: { tools: {} } }
  );

  // ── browser_open ──────────────────────────────────────────────────
  server.tool(
    'browser_open',
    'Open a URL in the browser. Launches browser if needed.',
    { url: z.string().describe('URL to navigate to') },
    async ({ url }) => {
      const resp = await conn.send({ action: 'navigate', url });
      return toolResult(resp);
    }
  );

  // ── browser_snapshot ──────────────────────────────────────────────
  server.tool(
    'browser_snapshot',
    'Capture the accessibility (ARIA) tree of the current page.',
    {
      mode: z
        .enum(['full', 'compact', 'interactive'])
        .optional()
        .describe('Snapshot mode: full (all nodes), compact (trimmed), interactive (actionable elements only)'),
      selector: z.string().optional().describe('CSS selector to scope the snapshot'),
    },
    async ({ mode, selector }) => {
      const cmd: Record<string, unknown> = { action: 'snapshot' };
      if (mode === 'compact') cmd.compact = true;
      if (mode === 'interactive') cmd.interactive = true;
      if (selector) cmd.selector = selector;
      const resp = await conn.send(cmd);
      return toolResult(resp);
    }
  );

  // ── browser_screenshot ────────────────────────────────────────────
  server.tool(
    'browser_screenshot',
    'Take a screenshot of the current page.',
    {
      path: z.string().optional().describe('File path to save the screenshot'),
      annotate: z.boolean().optional().describe('Annotate interactive elements with numbered labels'),
    },
    async ({ path, annotate }) => {
      const cmd: Record<string, unknown> = { action: 'screenshot' };
      if (path) cmd.path = path;
      if (annotate) cmd.annotate = true;
      const resp = await conn.send(cmd);
      return toolResult(resp);
    }
  );

  // ── browser_click ─────────────────────────────────────────────────
  server.tool(
    'browser_click',
    'Click an element by its snapshot ref (e.g. "@e12").',
    { ref: z.string().describe('Element ref from snapshot (e.g. "@e12")') },
    async ({ ref }) => {
      const resp = await conn.send({ action: 'click', selector: ref });
      return toolResult(resp);
    }
  );

  // ── browser_fill ──────────────────────────────────────────────────
  server.tool(
    'browser_fill',
    'Clear and fill an input element with text.',
    {
      ref: z.string().describe('Element ref from snapshot'),
      text: z.string().describe('Text to fill'),
    },
    async ({ ref, text }) => {
      const resp = await conn.send({ action: 'fill', selector: ref, value: text });
      return toolResult(resp);
    }
  );

  // ── browser_type ──────────────────────────────────────────────────
  server.tool(
    'browser_type',
    'Type text into an element keystroke-by-keystroke (does not clear first).',
    {
      ref: z.string().describe('Element ref from snapshot'),
      text: z.string().describe('Text to type'),
    },
    async ({ ref, text }) => {
      const resp = await conn.send({ action: 'type', selector: ref, text });
      return toolResult(resp);
    }
  );

  // ── browser_get ───────────────────────────────────────────────────
  server.tool(
    'browser_get',
    'Get information about the page or an element.',
    {
      what: z
        .enum(['title', 'url', 'text', 'value'])
        .describe('What to retrieve'),
      ref: z.string().optional().describe('Element ref (required for text/value)'),
    },
    async ({ what, ref }) => {
      let resp: Response;
      switch (what) {
        case 'title':
          resp = await conn.send({ action: 'title' });
          break;
        case 'url':
          resp = await conn.send({ action: 'url' });
          break;
        case 'text':
          if (!ref) return { content: [{ type: 'text' as const, text: 'Error: ref is required for text' }], isError: true };
          resp = await conn.send({ action: 'gettext', selector: ref });
          break;
        case 'value':
          if (!ref) return { content: [{ type: 'text' as const, text: 'Error: ref is required for value' }], isError: true };
          resp = await conn.send({ action: 'inputvalue', selector: ref });
          break;
        default:
          return { content: [{ type: 'text' as const, text: `Unknown what: ${what}` }], isError: true };
      }
      return toolResult(resp);
    }
  );

  // ── browser_diff ──────────────────────────────────────────────────
  server.tool(
    'browser_diff',
    'Compare current page state against previous snapshot or screenshot.',
    {
      type: z
        .enum(['snapshot', 'screenshot'])
        .describe('Type of diff to perform'),
    },
    async ({ type }) => {
      const action = type === 'snapshot' ? 'diff_snapshot' : 'diff_screenshot';
      const cmd: Record<string, unknown> = { action };
      if (type === 'screenshot') {
        cmd.baseline = '';
      }
      const resp = await conn.send(cmd);
      return toolResult(resp);
    }
  );

  // ── browser_close ─────────────────────────────────────────────────
  server.tool(
    'browser_close',
    'Close the browser and shut down the daemon.',
    {},
    async () => {
      const resp = await conn.send({ action: 'close' });
      return toolResult(resp);
    }
  );

  // ── browser_navigate ──────────────────────────────────────────────
  server.tool(
    'browser_navigate',
    'Navigate back, forward, or reload the current page.',
    {
      action: z
        .enum(['back', 'forward', 'reload'])
        .describe('Navigation action'),
    },
    async ({ action }) => {
      const resp = await conn.send({ action });
      return toolResult(resp);
    }
  );

  // ── browser_press ─────────────────────────────────────────────────
  server.tool(
    'browser_press',
    'Press a keyboard key or key combination (e.g. "Enter", "Control+a").',
    {
      key: z.string().describe('Key or key combination to press'),
    },
    async ({ key }) => {
      const resp = await conn.send({ action: 'press', key });
      return toolResult(resp);
    }
  );

  // ── browser_wait ──────────────────────────────────────────────────
  server.tool(
    'browser_wait',
    'Wait for a condition: element selector, URL, or load state.',
    {
      condition: z
        .string()
        .describe('Condition type: "selector", "url", or "loadstate"'),
      value: z
        .string()
        .optional()
        .describe('Condition value: CSS selector, URL pattern, or load state'),
    },
    async ({ condition, value }) => {
      let resp: Response;
      switch (condition) {
        case 'selector':
          resp = await conn.send({ action: 'wait', selector: value });
          break;
        case 'url':
          resp = await conn.send({ action: 'waitforurl', url: value ?? '' });
          break;
        case 'loadstate':
          resp = await conn.send({
            action: 'waitforloadstate',
            state: (value ?? 'load') as 'load' | 'domcontentloaded' | 'networkidle',
          });
          break;
        default:
          // Treat as selector for backward compat
          resp = await conn.send({ action: 'wait', selector: condition });
          break;
      }
      return toolResult(resp);
    }
  );

  return server;
}

// ---------------------------------------------------------------------------
// Entry point: start MCP server
// ---------------------------------------------------------------------------

export interface McpServerOptions {
  /** Transport mode. Default: stdio */
  transport?: 'stdio' | 'sse';
  /** SSE port (only for sse transport). Default: 3100 */
  ssePort?: number;
  /** Daemon session name */
  session?: string;
}

export async function startMcpServer(options: McpServerOptions = {}): Promise<void> {
  const { transport = 'stdio', ssePort = 3100, session } = options;

  const conn = new DaemonConnection(session);
  await conn.connect();

  const mcpServer = createMcpServer(conn);

  if (transport === 'stdio') {
    const stdioTransport = new StdioServerTransport();
    await mcpServer.connect(stdioTransport);
  } else if (transport === 'sse') {
    const http = await import('http');
    let sseTransport: SSEServerTransport | null = null;

    const httpServer = http.createServer(async (req, res) => {
      if (req.url === '/sse' && req.method === 'GET') {
        sseTransport = new SSEServerTransport('/messages', res);
        await mcpServer.connect(sseTransport);
        return;
      }
      if (req.url === '/messages' && req.method === 'POST') {
        if (!sseTransport) {
          res.writeHead(400);
          res.end('SSE not connected');
          return;
        }
        await sseTransport.handlePostMessage(req, res);
        return;
      }
      res.writeHead(404);
      res.end('Not found');
    });

    httpServer.listen(ssePort, () => {
      // Ready on SSE port
    });
  }

  // Handle shutdown
  const cleanup = () => {
    conn.disconnect();
    process.exit(0);
  };
  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
}

// Allow running directly: node dist/mcp-server.js [--sse] [--port N] [--session S]
if (
  process.argv[1]?.endsWith('mcp-server.js') ||
  process.argv[1]?.endsWith('mcp-server.ts')
) {
  const args = process.argv.slice(2);
  const isSSE = args.includes('--sse');
  const portIdx = args.indexOf('--port');
  const port = portIdx >= 0 ? parseInt(args[portIdx + 1], 10) : undefined;
  const sessionIdx = args.indexOf('--session');
  const session = sessionIdx >= 0 ? args[sessionIdx + 1] : undefined;

  startMcpServer({
    transport: isSSE ? 'sse' : 'stdio',
    ssePort: port,
    session,
  }).catch((err) => {
    console.error('MCP Server error:', err);
    process.exit(1);
  });
}
