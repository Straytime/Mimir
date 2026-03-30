/**
 * Normalize LLM-generated footnotes (`[^ref_N]`) to sequential `[^1]`, `[^2]`, etc.
 *
 * Handles:
 * - Non-sequential ref numbers (ref_49, ref_162 → 1, 2)
 * - Underscore variants (ref_49 vs ref49) matched via normalized key
 * - Orphan definitions (def without inline ref) are dropped
 * - Orphan refs (inline ref without def) get a placeholder definition
 * - Duplicate inline refs (same key used multiple times) share the same number
 */
export function normalizeFootnotes(md: string): string {
  if (!md) return md;

  // Quick check: if no footnote-like patterns exist, return as-is
  if (!/\[\^ref_?\d+\]/.test(md)) return md;

  // --- Phase 1: Scan inline refs and assign sequential numbers ---
  const inlineRefPattern = /\[\^(ref_?\d+)\](?!:)/g;
  const keyMap = new Map<string, number>(); // normalizedKey → seqNumber
  const originalToNormalized = new Map<string, string>(); // originalKey → normalizedKey
  let seq = 0;

  // Collect all inline refs in order of first appearance
  let match: RegExpExecArray | null;
  while ((match = inlineRefPattern.exec(md)) !== null) {
    const originalKey = match[1];
    const normKey = normalizeKey(originalKey);
    originalToNormalized.set(originalKey, normKey);
    if (!keyMap.has(normKey)) {
      keyMap.set(normKey, ++seq);
    }
  }

  if (seq === 0) return md;

  // --- Phase 2: Scan definition lines ---
  const defLinePattern = /^\[\^(ref_?\d+)\]:\s*(.*)$/gm;
  const defMap = new Map<string, string>(); // normalizedKey → definition content

  while ((match = defLinePattern.exec(md)) !== null) {
    const originalKey = match[1];
    const normKey = normalizeKey(originalKey);
    const content = match[2];
    defMap.set(normKey, content);
  }

  // --- Phase 3: Replace inline refs with sequential numbers ---
  let result = md.replace(
    /\[\^(ref_?\d+)\](?!:)/g,
    (_full, key: string) => {
      const normKey = normalizeKey(key);
      const num = keyMap.get(normKey);
      return num != null ? `[^${num}]` : _full;
    },
  );

  // --- Phase 4: Remove all original definition lines ---
  result = result.replace(/^\[\^ref_?\d+\]:\s*.*$/gm, "");

  // Clean up excess blank lines left by removed definitions
  result = result.replace(/\n{3,}/g, "\n\n");
  // Remove trailing whitespace-only lines but keep final newline if present
  result = result.replace(/\n+$/, "");

  // --- Phase 5: Append new sequential definitions ---
  const defLines: string[] = [];
  for (const [normKey, num] of keyMap) {
    const content = defMap.get(normKey);
    if (content) {
      defLines.push(`[^${num}]: ${content}`);
    } else {
      defLines.push(`[^${num}]: (来源缺失)`);
    }
  }

  if (defLines.length > 0) {
    result = result + "\n\n" + defLines.join("\n");
  }

  return result;
}

/** Normalize a footnote key by removing underscores and lowercasing. */
function normalizeKey(key: string): string {
  return key.replace(/_/g, "").toLowerCase();
}
