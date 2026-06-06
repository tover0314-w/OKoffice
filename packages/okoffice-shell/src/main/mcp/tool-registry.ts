import type { ToolCategory, ToolSpec } from '@shared/types';

const CATEGORY_CONFIG: Record<string, { label: string; icon: string }> = {
  pdf: { label: 'PDF', icon: 'file-pdf' },
  word: { label: 'Word', icon: 'file-word' },
  sheet: { label: 'Sheets', icon: 'file-excel' },
  deck: { label: 'Decks', icon: 'file-ppt' },
  office: { label: 'Office', icon: 'folder' },
};

const CATEGORY_PREFIX_MAP: Record<string, string> = {
  pdf: 'pdf_',
  word: 'word_',
  sheet: 'sheet_',
  deck: 'deck_',
  office: 'office_',
};

function extractCategory(toolName: string): string | null {
  for (const [category, prefix] of Object.entries(CATEGORY_PREFIX_MAP)) {
    if (toolName.startsWith(prefix)) {
      return category;
    }
  }
  return null;
}

export class ToolRegistry {
  private tools: ToolSpec[] = [];
  private categoryMap: Map<string, ToolCategory> = new Map();
  private uncategorized: ToolSpec[] = [];

  loadTools(tools: ToolSpec[]): void {
    this.tools = [...tools];
    this.rebuildCategories();
  }

  getCategories(): ToolCategory[] {
    return Array.from(this.categoryMap.values());
  }

  getAllTools(): ToolSpec[] {
    return [...this.tools];
  }

  getToolsByCategory(category: string): ToolSpec[] {
    const cat = this.categoryMap.get(category);
    return cat ? [...cat.tools] : [];
  }

  findTool(name: string): ToolSpec | undefined {
    return this.tools.find((t) => t.name === name);
  }

  search(query: string): ToolSpec[] {
    const lowerQuery = query.toLowerCase();
    return this.tools.filter(
      (t) =>
        t.name.toLowerCase().includes(lowerQuery) ||
        t.description.toLowerCase().includes(lowerQuery),
    );
  }

  getFunctionCallingFormat(): Array<{
    type: 'function';
    function: { name: string; description: string; parameters: Record<string, unknown> };
  }> {
    return this.tools
      .filter((t) => t.implemented)
      .map((t) => ({
        type: 'function' as const,
        function: {
          name: t.name,
          description: t.description,
          parameters: t.inputSchema ?? { type: 'object', properties: {} },
        },
      }));
  }

  private rebuildCategories(): void {
    this.categoryMap.clear();
    this.uncategorized = [];

    for (const tool of this.tools) {
      const category = tool.category ?? extractCategory(tool.name);

      if (category && CATEGORY_CONFIG[category]) {
        let cat = this.categoryMap.get(category);
        if (!cat) {
          const config = CATEGORY_CONFIG[category];
          cat = {
            name: category,
            label: config.label,
            icon: config.icon,
            tools: [],
          };
          this.categoryMap.set(category, cat);
        }
        cat.tools.push(tool);
      } else {
        this.uncategorized.push(tool);
      }
    }
  }
}
