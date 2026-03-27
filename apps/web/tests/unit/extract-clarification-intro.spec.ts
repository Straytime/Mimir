import { describe, expect, it } from "vitest";

import { extractClarificationIntro } from "@/features/research/utils/clarification-text";
import type { ClarificationQuestionSet } from "@/lib/contracts";

function makeQuestionSet(questions: string[]): ClarificationQuestionSet {
  return {
    questions: questions.map((q, i) => ({
      question_id: `q_${i}`,
      question: q,
      options: [
        { option_id: "o_1", label: "选项 A" },
        { option_id: "o_2", label: "选项 B" },
      ],
    })),
  };
}

describe("extractClarificationIntro", () => {
  it("returns intro text before the first question line", () => {
    const text = [
      "为了更好地理解你的研究需求，请回答以下问题：",
      "",
      "1. 你希望报告侧重哪个方面？",
      "   A. 技术细节",
      "   B. 商业分析",
    ].join("\n");
    const qs = makeQuestionSet(["你希望报告侧重哪个方面？"]);

    const intro = extractClarificationIntro(text, qs);
    expect(intro).toBe("为了更好地理解你的研究需求，请回答以下问题：");
  });

  it("returns empty string when text starts with the first question", () => {
    const text = [
      "你希望报告侧重哪个方面？",
      "   A. 技术细节",
      "   B. 商业分析",
    ].join("\n");
    const qs = makeQuestionSet(["你希望报告侧重哪个方面？"]);

    const intro = extractClarificationIntro(text, qs);
    expect(intro).toBe("");
  });

  it("returns full text when anchor question is not found", () => {
    const text = "这段文本完全不包含任何问题。";
    const qs = makeQuestionSet(["不存在的问题？"]);

    const intro = extractClarificationIntro(text, qs);
    expect(intro).toBe(text);
  });

  it("returns full text when questions array is empty", () => {
    const text = "这段文本完全不包含任何问题。";
    const qs = makeQuestionSet([]);

    const intro = extractClarificationIntro(text, qs);
    expect(intro).toBe(text);
  });
});
