import { describe, expect, test } from "vitest";
import { normalizeFootnotes } from "@/features/research/utils/normalize-footnotes";

describe("normalizeFootnotes", () => {
  test("returns unchanged markdown when no footnotes present", () => {
    const md = "# Hello\n\nNo footnotes here.";
    expect(normalizeFootnotes(md)).toBe(md);
  });

  test("renumbers non-sequential ref keys to sequential 1,2,3", () => {
    const md = [
      "结论A[^ref_49]与B[^ref_162]",
      "",
      "[^ref_49]: [来源49](https://a.com/49)",
      "[^ref_162]: [来源162](https://a.com/162)",
    ].join("\n");
    const result = normalizeFootnotes(md);
    expect(result).toContain("[^1]");
    expect(result).toContain("[^2]");
    expect(result).not.toContain("[^ref_49]");
    expect(result).not.toContain("[^ref_162]");
    // definitions also renumbered
    expect(result).toContain("[^1]: [来源49]");
    expect(result).toContain("[^2]: [来源162]");
  });

  test("handles duplicate inline refs (same ref used multiple times)", () => {
    const md = [
      "第一处[^ref_3]，第二处也引用[^ref_3]",
      "",
      "[^ref_3]: [来源](https://a.com)",
    ].join("\n");
    const result = normalizeFootnotes(md);
    // Both occurrences get the same number
    const matches = result.match(/\[\^1\]/g);
    expect(matches?.length).toBe(3); // 2 inline + 1 definition
  });

  test("drops orphan definitions that have no inline ref", () => {
    const md = [
      "只用了[^ref_1]",
      "",
      "[^ref_1]: [来源1](https://a.com/1)",
      "[^ref_2]: [来源2](https://a.com/2)",
    ].join("\n");
    const result = normalizeFootnotes(md);
    expect(result).toContain("[^1]");
    expect(result).not.toContain("[^2]");
    expect(result).not.toContain("来源2");
  });

  test("preserves ref without matching definition (keeps inline ref)", () => {
    // LLM wrote ref but forgot definition - still generate the ref so remark-gfm
    // can at least show it (even if as text). Better: generate empty def.
    const md = "结论[^ref_49]来源\n\n[^ref_50]: [来源50](https://a.com)";
    const result = normalizeFootnotes(md);
    // ref_49 used inline → renumbered to 1, should have placeholder def
    expect(result).toContain("[^1]");
    expect(result).toContain("[^1]:");
  });

  test("handles keys without underscore (ref49 vs ref_49) via normalization", () => {
    const md = [
      "结论[^ref_49]来源",
      "",
      "[^ref49]: [来源](https://a.com)",
    ].join("\n");
    const result = normalizeFootnotes(md);
    // Should match ref_49 to ref49 and normalize
    expect(result).toContain("[^1]");
    expect(result).toContain("[^1]: [来源]");
  });

  test("already sequential refs (ref_1, ref_2) still get normalized", () => {
    const md = [
      "A[^ref_1]和B[^ref_2]",
      "",
      "[^ref_1]: [来源1](https://a.com/1)",
      "[^ref_2]: [来源2](https://a.com/2)",
    ].join("\n");
    const result = normalizeFootnotes(md);
    expect(result).toContain("[^1]");
    expect(result).toContain("[^2]");
  });

  test("handles empty string", () => {
    expect(normalizeFootnotes("")).toBe("");
  });

  test("preserves non-footnote content exactly", () => {
    const md = [
      "# Title",
      "",
      "Some **bold** and [link](url) content[^ref_1].",
      "",
      "```code block```",
      "",
      "[^ref_1]: [Source](https://a.com)",
    ].join("\n");
    const result = normalizeFootnotes(md);
    expect(result).toContain("# Title");
    expect(result).toContain("Some **bold** and [link](url) content[^1].");
    expect(result).toContain("```code block```");
  });
});
