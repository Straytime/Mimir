import type { ClarificationQuestionSet } from "@/lib/contracts";

/**
 * Extract the introductory text that precedes the first question in raw
 * clarification output. When the LLM emits structured questions, the raw
 * text often contains both a natural-language preamble and the questions
 * themselves. This function returns only the preamble so the UI can show
 * it without duplicating the questions already rendered as option cards.
 */
export function extractClarificationIntro(
  clarificationText: string,
  questionSet: ClarificationQuestionSet,
): string {
  if (questionSet.questions.length === 0) {
    return clarificationText;
  }

  const anchor = questionSet.questions[0].question;
  const idx = clarificationText.indexOf(anchor);

  if (idx === -1) {
    return clarificationText;
  }

  // Walk back to the start of the line containing the anchor
  const lineStart = clarificationText.lastIndexOf("\n", idx - 1);
  const intro = clarificationText.slice(0, lineStart === -1 ? 0 : lineStart).trim();

  return intro;
}
