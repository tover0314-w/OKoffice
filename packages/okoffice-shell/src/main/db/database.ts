import Database from 'better-sqlite3';
import { app } from 'electron';
import path from 'node:path';
import { DEFAULTS } from '@shared/constants';

let instance: Database.Database | null = null;

export function getDatabasePath(): string {
  const userDataPath = app.getPath('userData');
  return path.join(userDataPath, DEFAULTS.DB_NAME);
}

export function getDatabase(): Database.Database {
  if (instance === null) {
    throw new Error('Database has not been initialized. Call initDatabase() first.');
  }
  return instance;
}

export function initDatabase(dbPath?: string): Database.Database {
  if (instance !== null) {
    return instance;
  }

  const resolvedPath = dbPath ?? getDatabasePath();
  instance = new Database(resolvedPath);

  instance.pragma('journal_mode = WAL');
  instance.pragma('foreign_keys = ON');
  instance.pragma('synchronous = NORMAL');

  return instance;
}

export function closeDatabase(): void {
  if (instance !== null) {
    instance.close();
    instance = null;
  }
}
