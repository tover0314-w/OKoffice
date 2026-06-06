import { WebSocketServer, WebSocket } from 'ws';
import { DEFAULTS } from '@shared/constants';
import type { StreamEvent } from '@shared/types';

export interface WsBroadcaster {
  emit(event: StreamEvent): void;
  close(): void;
  getClientCount(): number;
}

export function startWsServer(port: number = DEFAULTS.APP_PORT): WsBroadcaster {
  const clients = new Set<WebSocket>();

  const wss = new WebSocketServer({ port });

  wss.on('connection', (ws: WebSocket) => {
    clients.add(ws);

    ws.on('close', () => {
      clients.delete(ws);
    });

    ws.on('error', () => {
      clients.delete(ws);
    });
  });

  const broadcaster: WsBroadcaster = {
    emit(event: StreamEvent): void {
      const payload = JSON.stringify(event);

      for (const client of clients) {
        if (client.readyState === WebSocket.OPEN) {
          client.send(payload);
        }
      }
    },

    close(): void {
      for (const client of clients) {
        if (client.readyState === WebSocket.OPEN || client.readyState === WebSocket.CONNECTING) {
          client.close();
        }
      }
      clients.clear();
      wss.close();
    },

    getClientCount(): number {
      return clients.size;
    },
  };

  return broadcaster;
}
