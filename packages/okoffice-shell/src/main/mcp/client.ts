import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { DEFAULTS } from '@shared/constants';
import type { MCPStatus, ToolSpec } from '@shared/types';

export interface McpClientEvents {
  statusChanged: (status: MCPStatus) => void;
  error: (error: Error) => void;
}

const MAX_RESTART_RETRIES = 3;
const BASE_BACKOFF_MS = 1000;

type McpClientEventMap = {
  [K in keyof McpClientEvents]: McpClientEvents[K];
};

export class McpClient extends EventEmitter {
  private client: Client | null = null;
  private transport: StdioClientTransport | null = null;
  private subprocess: ChildProcess | null = null;
  private toolList: ToolSpec[] = [];
  private status: MCPStatus = {
    connected: false,
    toolCount: 0,
  };
  private startedAt: number = 0;
  private retryCount = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private shuttingDown = false;

  constructor(
    private readonly command: string = DEFAULTS.MCP_COMMAND,
    private readonly args: string[] = [...DEFAULTS.MCP_ARGS],
  ) {
    super();
  }

  async start(): Promise<void> {
    this.shuttingDown = false;
    await this.connect();
  }

  async stop(): Promise<void> {
    this.shuttingDown = true;
    this.cancelRetry();

    try {
      if (this.client) {
        await this.client.close();
      }
    } catch {
      // best-effort close
    }

    this.killSubprocess();

    this.client = null;
    this.transport = null;
    this.updateStatus({ connected: false, toolCount: 0, serverPid: undefined, uptime: undefined });
  }

  async restart(): Promise<void> {
    this.retryCount = 0;
    await this.stop();
    await this.start();
  }

  async callTool(name: string, args: Record<string, unknown>): Promise<unknown> {
    if (!this.client) {
      throw new Error('MCP client is not connected');
    }

    const result = await this.client.callTool({ name, arguments: args });
    return result;
  }

  getStatus(): MCPStatus {
    return { ...this.status };
  }

  getToolList(): ToolSpec[] {
    return [...this.toolList];
  }

  private async connect(): Promise<void> {
    this.subprocess = spawn(this.command, this.args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
    });

    if (!this.subprocess.pid) {
      throw new Error(`Failed to spawn MCP server: ${this.command}`);
    }

    this.setupSubprocessHandlers();

    this.transport = new StdioClientTransport({
      stdin: this.subprocess.stdin!,
      stdout: this.subprocess.stdout!,
      stderr: this.subprocess.stderr!,
    });

    this.client = new Client(
      { name: 'okoffice-shell', version: '0.1.0' },
      { capabilities: {} },
    );

    await this.client.connect(this.transport);

    // Cache the tool manifest
    const toolsResponse = await this.client.listTools();
    this.toolList = (toolsResponse.tools as ToolSpec[]) ?? [];

    this.startedAt = Date.now();
    this.retryCount = 0;
    this.updateStatus({
      connected: true,
      toolCount: this.toolList.length,
      serverPid: this.subprocess.pid,
      uptime: 0,
    });
  }

  private setupSubprocessHandlers(): void {
    if (!this.subprocess) return;

    this.subprocess.on('error', (err: Error) => {
      this.emit('error', err);
      this.updateStatus({
        connected: false,
        toolCount: 0,
        lastError: err.message,
      });
      this.scheduleRestart();
    });

    this.subprocess.on('exit', (code: number | null) => {
      if (this.shuttingDown) return;

      const message = `MCP server exited with code ${code}`;
      this.emit('error', new Error(message));
      this.updateStatus({
        connected: false,
        toolCount: 0,
        lastError: message,
      });
      this.scheduleRestart();
    });
  }

  private scheduleRestart(): void {
    if (this.shuttingDown) return;
    if (this.retryCount >= MAX_RESTART_RETRIES) {
      this.emit('error', new Error(`MCP server failed after ${MAX_RESTART_RETRIES} restart attempts`));
      return;
    }

    const backoffMs = BASE_BACKOFF_MS * Math.pow(2, this.retryCount);
    this.retryCount += 1;

    this.retryTimer = setTimeout(async () => {
      this.retryTimer = null;
      try {
        await this.stop();
        await this.start();
      } catch (err) {
        this.emit('error', err instanceof Error ? err : new Error(String(err)));
      }
    }, backoffMs);
  }

  private cancelRetry(): void {
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }

  private killSubprocess(): void {
    if (this.subprocess && !this.subprocess.killed) {
      try {
        this.subprocess.kill('SIGTERM');
      } catch {
        // process may already be dead
      }
    }
    this.subprocess = null;
  }

  private updateStatus(partial: Partial<MCPStatus>): void {
    this.status = {
      ...this.status,
      ...partial,
      uptime: this.status.connected ? Math.floor((Date.now() - this.startedAt) / 1000) : undefined,
    };
    this.emit('statusChanged', this.getStatus());
  }
}
