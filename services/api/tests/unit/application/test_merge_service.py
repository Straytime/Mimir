from app.application.dto.research import CollectedSourceItem
from app.application.services.merge import SourceMergeService


def test_same_source_merge_combines_info_and_reassigns_predictable_refer_numbers() -> None:
    service = SourceMergeService()

    merged = service.merge(
        (
            CollectedSourceItem(
                title="来源 A",
                link="https://example.com/a",
                info="第一条信息。",
            ),
            CollectedSourceItem(
                title="来源 B",
                link="https://example.com/b",
                info="第二条信息。",
            ),
            CollectedSourceItem(
                title="来源 A 更新",
                link="https://example.com/a",
                info="第三条信息。",
            ),
        )
    )

    assert [source.refer for source in merged] == ["ref_1", "ref_2"]
    assert merged[0].title == "来源 A"
    assert merged[0].link == "https://example.com/a"
    assert merged[0].info == "第一条信息。\n第三条信息。"
    assert merged[1].title == "来源 B"


def test_same_source_merge_deduplicates_identical_info_segments_without_reordering() -> None:
    service = SourceMergeService()

    merged = service.merge(
        (
            CollectedSourceItem(
                title="来源 A",
                link="https://example.com/a",
                info="相同信息。",
            ),
            CollectedSourceItem(
                title="来源 A",
                link="https://example.com/a",
                info="相同信息。",
            ),
            CollectedSourceItem(
                title="来源 C",
                link="https://example.com/c",
                info="另一条信息。",
            ),
        )
    )

    assert len(merged) == 2
    assert merged[0].refer == "ref_1"
    assert merged[0].info == "相同信息。"
    assert merged[1].refer == "ref_2"
