import EE from 'eventemitter3';
import type { StreamEvent } from '@shared/types';
import api from './bridge';

type EventMap = {
  [E in StreamEvent['type']]?: Extract<StreamEvent, { type: E }>;
};

type EventCallback<T extends StreamEvent['type']> = (
  payload: Extract<StreamEvent, { type: T }>,
) => void;

const emitter = new EE.EventEmitter<EventMap>();
let listening = false;
let unsubscribeFn: (() => void) | null = null;

function ensureListening(): void {
  if (listening) return;
  listening = true;

  unsubscribeFn = api.onEvent((event: StreamEvent) => {
    emitter.emit(event.type as keyof EventMap, event as never);
  });
}

function stopListeningIfEmpty(): void {
  if (emitter.eventNames().length > 0) return;
  if (unsubscribeFn) {
    unsubscribeFn();
    unsubscribeFn = null;
  }
  listening = false;
}

export function subscribe<T extends StreamEvent['type']>(
  eventType: T,
  callback: EventCallback<T>,
): void {
  ensureListening();
  emitter.on(eventType, callback as never);
}

export function unsubscribe<T extends StreamEvent['type']>(
  eventType: T,
  callback: EventCallback<T>,
): void {
  emitter.off(eventType, callback as never);
  stopListeningIfEmpty();
}

export { emitter };
