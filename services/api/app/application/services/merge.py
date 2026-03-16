from collections import OrderedDict
from collections.abc import Sequence

from app.application.dto.research import CollectedSourceItem, FormattedSource


class SourceMergeService:
    def merge(
        self,
        items: Sequence[CollectedSourceItem],
    ) -> tuple[FormattedSource, ...]:
        merged_map: OrderedDict[str, dict[str, object]] = OrderedDict()

        for item in items:
            key = _source_key(link=item.link, title=item.title)
            if key not in merged_map:
                merged_map[key] = {
                    "title": item.title,
                    "link": item.link,
                    "infos": [item.info],
                }
                continue

            existing_infos = merged_map[key]["infos"]
            assert isinstance(existing_infos, list)
            if item.info not in existing_infos:
                existing_infos.append(item.info)

        merged_sources: list[FormattedSource] = []
        for index, merged in enumerate(merged_map.values(), start=1):
            title = merged["title"]
            link = merged["link"]
            infos = merged["infos"]
            assert isinstance(title, str)
            assert isinstance(link, str)
            assert isinstance(infos, list)
            merged_sources.append(
                FormattedSource(
                    refer=f"ref_{index}",
                    title=title,
                    link=link,
                    info="\n".join(info for info in infos if isinstance(info, str)),
                )
            )

        return tuple(merged_sources)


def _source_key(*, link: str, title: str) -> str:
    normalized_link = link.strip().lower()
    if normalized_link:
        return normalized_link
    return title.strip().lower()
