from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.application.ports.delivery import ArtifactStore
from app.application.services.tasks import TaskService
from app.core.ids import hash_secret
from app.domain.enums import (
    AccessTokenResourceType,
    ClarificationMode,
    FreshnessRequirement,
    OutputFormat,
    RevisionStatus,
)
from app.domain.schemas import RequirementDetail
from app.domain.tokens import TaskTokenPayload
from app.infrastructure.db.models import (
    ArtifactRecord,
    CollectedSourceRecord,
    ResearchTaskRecord,
    TaskRevisionRecord,
)


@dataclass(frozen=True, slots=True)
class SeededDeliveredTask:
    task_id: str
    task_token: str
    trace_id: str
    revision_id: str
    revision_number: int
    markdown_storage_key: str
    pdf_storage_key: str
    artifact_storage_key: str


async def seed_delivered_task(
    *,
    session: Session,
    task_service: TaskService,
    artifact_store: ArtifactStore,
    now: datetime,
    suffix: str = "seed",
    include_artifacts: bool = True,
    include_sources: bool = True,
    expires_at: datetime | None = None,
) -> SeededDeliveredTask:
    task_id = f"tsk_{suffix}"
    revision_id = f"rev_{suffix}_1"
    trace_id = f"trc_{suffix}"
    task_token = task_service.task_token_signer.sign(
        TaskTokenPayload(
            task_id=task_id,
            issued_at=now,
            expires_at=now + timedelta(hours=24),
        )
    )
    expiry = expires_at or (now + timedelta(minutes=30))

    requirement_detail = RequirementDetail(
        research_goal="分析中国 AI 搜索产品竞争格局",
        domain="互联网 / AI 产品",
        requirement_details="聚焦中国市场，偏商业分析，覆盖近两年变化。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
        raw_llm_output={
            "research_goal": "分析中国 AI 搜索产品竞争格局",
            "domain": "互联网 / AI 产品",
        },
    )

    session.add(
        ResearchTaskRecord(
            task_id=task_id,
            trace_id=trace_id,
            status="awaiting_feedback",
            phase="delivered",
            clarification_mode=ClarificationMode.NATURAL.value,
            initial_query="请分析中国 AI 搜索产品的竞争格局。",
            client_timezone="Asia/Shanghai",
            client_locale="zh-CN",
            ip_hash="ip-hash",
            task_token_hash=hash_secret(task_token),
            active_revision_id=revision_id,
            active_revision_number=1,
            created_at=now - timedelta(minutes=20),
            updated_at=now,
            expires_at=expiry,
            cleanup_pending=False,
            connect_deadline_at=now - timedelta(minutes=19),
        )
    )
    session.add(
        TaskRevisionRecord(
            revision_id=revision_id,
            task_id=task_id,
            revision_number=1,
            revision_status=RevisionStatus.COMPLETED.value,
            started_at=now - timedelta(minutes=20),
            finished_at=now - timedelta(minutes=1),
            requirement_detail_json=requirement_detail.model_dump(
                mode="json",
                exclude_none=True,
            ),
            collect_agent_calls_used=3,
            sandbox_id=None,
        )
    )
    session.flush()

    artifact_storage_key = f"tasks/{task_id}/{revision_id}/artifacts/art_{suffix}_chart.png"
    markdown_storage_key = f"tasks/{task_id}/{revision_id}/downloads/mimir-report.zip"
    pdf_storage_key = f"tasks/{task_id}/{revision_id}/downloads/mimir-report.pdf"

    if include_artifacts:
        await artifact_store.put(
            artifact_storage_key,
            b"png-chart",
            "image/png",
        )
        await artifact_store.put(
            markdown_storage_key,
            b"zip-bytes",
            "application/zip",
        )
        await artifact_store.put(
            pdf_storage_key,
            b"%PDF-1.4\nseed\n%%EOF",
            "application/pdf",
        )
        session.add_all(
            [
                ArtifactRecord(
                    artifact_id=f"art_{suffix}_img",
                    task_id=task_id,
                    revision_id=revision_id,
                    resource_type=AccessTokenResourceType.ARTIFACT.value,
                    filename="chart_market_share.png",
                    mime_type="image/png",
                    storage_key=artifact_storage_key,
                    byte_size=9,
                    metadata_json=None,
                    created_at=now - timedelta(minutes=2),
                ),
                ArtifactRecord(
                    artifact_id=f"art_{suffix}_zip",
                    task_id=task_id,
                    revision_id=revision_id,
                    resource_type=AccessTokenResourceType.MARKDOWN_DOWNLOAD.value,
                    filename="mimir-report.zip",
                    mime_type="application/zip",
                    storage_key=markdown_storage_key,
                    byte_size=9,
                    metadata_json={"word_count": 1200},
                    created_at=now - timedelta(minutes=2),
                ),
                ArtifactRecord(
                    artifact_id=f"art_{suffix}_pdf",
                    task_id=task_id,
                    revision_id=revision_id,
                    resource_type=AccessTokenResourceType.PDF_DOWNLOAD.value,
                    filename="mimir-report.pdf",
                    mime_type="application/pdf",
                    storage_key=pdf_storage_key,
                    byte_size=18,
                    metadata_json={"word_count": 1200},
                    created_at=now - timedelta(minutes=2),
                ),
            ]
        )

    if include_sources:
        session.add_all(
            [
                CollectedSourceRecord(
                    task_id=task_id,
                    revision_id=revision_id,
                    subtask_id=f"sub_{suffix}_1",
                    tool_call_id=f"call_{suffix}_1",
                    title="某公司发布会回顾",
                    link="https://example.com/article-1",
                    info="某产品在 2025 年发布企业版能力。",
                    source_key="c9fb1023adc25cbc7f7ea32cbf1cabf347d8aca007c3b5f8b4a3d6f5eabcb553",
                    refer=None,
                    is_merged=False,
                    created_at=now - timedelta(minutes=10),
                ),
                CollectedSourceRecord(
                    task_id=task_id,
                    revision_id=revision_id,
                    subtask_id=f"sub_{suffix}_2",
                    tool_call_id=f"call_{suffix}_2",
                    title="行业分析报告",
                    link="https://example.com/article-2",
                    info="中国市场竞争正在加速。",
                    source_key="8589f577a91671e1dab40a8b04a67f36cde031df4c4df189d054054d9026a41e",
                    refer=None,
                    is_merged=False,
                    created_at=now - timedelta(minutes=9),
                ),
                CollectedSourceRecord(
                    task_id=task_id,
                    revision_id=revision_id,
                    subtask_id=f"sub_{suffix}_1",
                    tool_call_id=f"call_{suffix}_1",
                    title="某公司发布会回顾",
                    link="https://example.com/article-1",
                    info="某产品在 2025 年发布企业版能力。",
                    source_key="c9fb1023adc25cbc7f7ea32cbf1cabf347d8aca007c3b5f8b4a3d6f5eabcb553",
                    refer="ref_1",
                    is_merged=True,
                    created_at=now - timedelta(minutes=8),
                ),
            ]
        )

    session.commit()
    return SeededDeliveredTask(
        task_id=task_id,
        task_token=task_token,
        trace_id=trace_id,
        revision_id=revision_id,
        revision_number=1,
        markdown_storage_key=markdown_storage_key,
        pdf_storage_key=pdf_storage_key,
        artifact_storage_key=artifact_storage_key,
    )
