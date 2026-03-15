from enum import StrEnum


class TaskStatus(StrEnum):
    RUNNING = "running"
    AWAITING_USER_INPUT = "awaiting_user_input"
    AWAITING_FEEDBACK = "awaiting_feedback"
    TERMINATED = "terminated"
    FAILED = "failed"
    EXPIRED = "expired"
    PURGED = "purged"


class TaskPhase(StrEnum):
    CLARIFYING = "clarifying"
    ANALYZING_REQUIREMENT = "analyzing_requirement"
    PLANNING_COLLECTION = "planning_collection"
    COLLECTING = "collecting"
    SUMMARIZING_COLLECTION = "summarizing_collection"
    MERGING_SOURCES = "merging_sources"
    PREPARING_OUTLINE = "preparing_outline"
    WRITING_REPORT = "writing_report"
    DELIVERED = "delivered"
    PROCESSING_FEEDBACK = "processing_feedback"


class ClarificationMode(StrEnum):
    NATURAL = "natural"
    OPTIONS = "options"


class OutputFormat(StrEnum):
    GENERAL = "general"
    RESEARCH_REPORT = "research_report"
    BUSINESS_REPORT = "business_report"
    ACADEMIC_PAPER = "academic_paper"
    DEEP_ARTICLE = "deep_article"
    GUIDE = "guide"
    SHOPPING_RECOMMENDATION = "shopping_recommendation"


class FreshnessRequirement(StrEnum):
    HIGH = "high"
    NORMAL = "normal"


class AvailableAction(StrEnum):
    SUBMIT_CLARIFICATION = "submit_clarification"
    SUBMIT_FEEDBACK = "submit_feedback"
    DOWNLOAD_MARKDOWN = "download_markdown"
    DOWNLOAD_PDF = "download_pdf"


class RevisionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class CollectSummaryStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    RISK_BLOCKED = "risk_blocked"


class AccessTokenResourceType(StrEnum):
    MARKDOWN_DOWNLOAD = "markdown_download"
    PDF_DOWNLOAD = "pdf_download"
    ARTIFACT = "artifact"
