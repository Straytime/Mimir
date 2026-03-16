import type { FeedbackAcceptedResponse, FeedbackRequest } from "@/lib/contracts";
import { makeFeedbackAcceptedResponse } from "@/tests/fixtures/builders";
import { expect, test } from "vitest";

test("feedback request and accepted response fixtures stay aligned with the contract", () => {
  const request: FeedbackRequest = {
    feedback_text: "请补充竞品差异和商业化路径。",
  };
  const response: FeedbackAcceptedResponse = makeFeedbackAcceptedResponse();

  expect(request.feedback_text).toBe("请补充竞品差异和商业化路径。");
  expect(response).toMatchObject({
    accepted: true,
    revision_id: "rev_stage1",
    revision_number: 2,
  });
});
