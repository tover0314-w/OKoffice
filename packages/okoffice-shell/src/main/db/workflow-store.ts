import type Database from 'better-sqlite3';
import type { Workflow, WorkflowSummary, WorkflowDefinition } from '@shared/types';

export class WorkflowStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  list(): WorkflowSummary[] {
    const rows = this.db
      .prepare(
        `SELECT id, name, description, updated_at
         FROM workflows
         ORDER BY updated_at DESC`,
      )
      .all() as WorkflowSummaryRow[];

    return rows.map((row) => ({
      id: row.id,
      name: row.name,
      description: row.description,
      updatedAt: row.updated_at,
    }));
  }

  get(id: string): Workflow | null {
    const row = this.db
      .prepare(
        `SELECT id, name, description, definition, created_at, updated_at
         FROM workflows WHERE id = ?`,
      )
      .get(id) as WorkflowRow | undefined;

    if (!row) {
      return null;
    }

    return {
      id: row.id,
      name: row.name,
      description: row.description,
      definition: JSON.parse(row.definition) as WorkflowDefinition,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }

  save(workflow: Workflow): void {
    const now = new Date().toISOString();
    const definitionJson = JSON.stringify(workflow.definition);

    this.db
      .prepare(
        `INSERT INTO workflows (id, name, description, definition, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           name = excluded.name,
           description = excluded.description,
           definition = excluded.definition,
           updated_at = excluded.updated_at`,
      )
      .run(
        workflow.id,
        workflow.name,
        workflow.description,
        definitionJson,
        workflow.createdAt ?? now,
        now,
      );
  }

  delete(id: string): void {
    this.db.prepare('DELETE FROM workflows WHERE id = ?').run(id);
  }
}

interface WorkflowSummaryRow {
  id: string;
  name: string;
  description: string;
  updated_at: string;
}

interface WorkflowRow {
  id: string;
  name: string;
  description: string;
  definition: string;
  created_at: string;
  updated_at: string;
}
