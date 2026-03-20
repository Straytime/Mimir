import json
from dataclasses import asdict

from app.application.dto.invocation import PromptBundle
from app.application.dto.delivery import OutlineInvocation, WriterInvocation

# Chinese quotation marks used by PRD prompt template
_LDQ = "\u201c"  # left double quotation mark
_RDQ = "\u201d"  # right double quotation mark
_LSQ = "\u2018"  # left single quotation mark
_RSQ = "\u2019"  # right single quotation mark
_ELLIPSIS = "\u2026\u2026"  # Chinese ellipsis


def _build_outline_system_prompt(now_iso: str) -> str:
    return (
        "<\u80cc\u666f\u4e0e\u4efb\u52a1>\n"
        "\u4f60\u662f\u4e00\u4e2a\u6df1\u5ea6\u7814\u7a76\u67b6\u6784\u5e08\uff0c"
        "\u8bf7\u57fa\u4e8e\u7528\u6237\u7814\u7a76\u9700\u6c42\u548c\u4fe1\u606f"
        "\u83b7\u53d6\u7ed3\u679c\uff0c\u89c4\u5212\u6df1\u5ea6\u7814\u7a76\u7684"
        "\u5b9e\u4f53\u7ea6\u675f\u548c\u5927\u7eb2\u7ed3\u6784\u3002\n"
        "\u4f60\u7684\u4efb\u52a1\u662f\u5b9a\u4e49" + _LSQ
        + "\u5199\u4ec0\u4e48" + _RSQ + "\u548c" + _LSQ
        + "\u600e\u4e48\u5199" + _RSQ
        + "\uff0c\u4f60**\u7edd\u5bf9\u4e0d\u80fd**\u64b0\u5199\u5177\u4f53"
        "\u5185\u5bb9\uff0c\u4f60\u7684\u4ea7\u51fa\u5c06\u4f5c\u4e3a\u6307\u4ee4"
        "\u53d1\u9001\u7ed9\u4e0b\u6e38\u7684" + _LDQ
        + "\u64b0\u5199\u5458" + _RDQ
        + "\uff0c\u5f53\u524d\u65f6\u95f4\u662f" + now_iso + "\u3002\n"
        "1. \u7d27\u5bc6\u56f4\u7ed5\u7528\u6237\u9700\u6c42\u8bbe\u8ba1"
        "\u5927\u7eb2\uff0c\u4fdd\u8bc1\u7814\u7a76\u5185\u5bb9\u524d\u540e"
        "\u903b\u8f91\u5408\u7406\u3001\u901a\u7545\u65e0\u524d\u540e"
        "\u51b2\u7a81\u3002\n"
        "1.1 \u6b63\u6587\u5185\u90e8\u7ed3\u6784\u4ec5\u4e0b\u63a2"
        "\u4e00\u7ea7\u3002\n"
        "1.2 \u5176\u4e2d\u7ae0\u8282\u63cf\u8ff0\u5185\u5bb9**\u5fc5\u987b**"
        "\u6ee1\u8db3\u4ee5\u4e0b\u8981\u6c42\n"
        "- \u6307\u4ee4\u6027\u8bed\u6c14\uff1a\u4f7f\u7528"
        + _LDQ + "\u5206\u6790" + _RDQ + "\u3001"
        + _LDQ + "\u8bc4\u4f30" + _RDQ + "\u3001"
        + _LDQ + "\u901a\u8fc7...\u5c55\u793a..." + _RDQ + "\u3001"
        + _LDQ + "\u91cd\u70b9\u8ba8\u8bba" + _RDQ
        + "\u7b49\u8bcd\u6c47\u3002\n"
        "- \u5143\u6570\u636e\u89c6\u89d2\uff1a\u63cf\u8ff0\u8be5\u7ae0\u8282"
        "\u7684**\u529f\u80fd**\u548c**\u8303\u56f4**\uff0c\u800c\u4e0d\u662f"
        "**\u7ed3\u679c**\u3002\n"
        "- \u6570\u636e\u5360\u4f4d\u7b26\uff1a\u4e0d\u8981\u5199\u51fa"
        "\u5177\u4f53\u7684\u6570\u5b57\uff08\u5982 "
        + _LDQ + "92%" + _RDQ
        + "\uff09\uff0c\u800c\u8981\u5199"
        + _LDQ + "\u5f15\u7528\u76f8\u5173\u7edf\u8ba1\u6570\u636e" + _RDQ
        + "\u6216" + _LDQ + "\u91cf\u5316\u5206\u6790\u9700\u6c42\u5ea6"
        + _RDQ + "\u3002\n"
        "- \u5b9e\u4f53\u62bd\u8c61\u5316\uff1a\u4e0d\u8981\u8fc7\u5ea6"
        "\u7f57\u5217\u5177\u4f53\u5b9e\u4f53\uff0c\u9664\u975e\u5b83\u4eec"
        "\u662f\u7ae0\u8282\u6807\u9898\u7684\u4e3b\u4f53\u3002"
        "\u5e94\u4f7f\u7528" + _LDQ
        + "\u9009\u53d6\u4ee3\u8868\u6027XX" + _RDQ + "\u3001"
        + _LDQ + "\u5bf9\u6bd4\u4e3b\u6d41XX" + _RDQ
        + "\u7b49\u62bd\u8c61\u5316\u8868\u8ff0\u3002\n"
        "2. \u6307\u5b9a\u5f53\u524d\u7814\u7a76\u7684\u5b9e\u4f53\u5217\u8868"
        "\uff0c\u6b64\u5904\u7684\u5b9e\u4f53\u6307\u8981\u64b0\u5199\u7684"
        "\u7814\u7a76\u5185\u5bb9\u672c\u8eab\u8981\u56f4\u7ed5\u7684"
        "\u5bf9\u8c61\u3002\n"
        "3. **\u5b9e\u4f53\u7ea6\u675f\u4e0e\u5927\u7eb2\u5fc5\u987b\u4e25\u683c"
        "\u8003\u91cf\u4fe1\u606f\u83b7\u53d6\u7ed3\u679c\uff0c\u4fdd\u8bc1"
        "\u5df2\u6709\u4fe1\u606f\u53ef\u652f\u6491**\u3002\n"
        "<\u80cc\u666f\u4e0e\u4efb\u52a1>\n"
        "\n"
        "<\u8f93\u51fa\u683c\u5f0f>\n"
        "\u53c2\u8003\u4ee5\u4e0b json \u683c\u5f0f\u76f4\u63a5"
        "\u8f93\u51fa\u4f60\u7684\u751f\u6210\u7ed3\u679c\u3002\n"
        "{\n"
        '    "research_outline": {\n'
        '        "\u6807\u9898": {\n'
        '            "title": ""\n'
        "        },\n"
        '        "section_1": {\n'
        '            "title": "",\n'
        '            "description": ""\n'
        "        },\n"
        "        " + _ELLIPSIS + "\n"
        '        "section_n": {\n'
        '            "title": "",\n'
        '            "description": ""\n'
        "        },\n"
        '        "\u53c2\u8003\u6765\u6e90": {\n'
        '            "title": "\u53c2\u8003\u6765\u6e90",\n'
        '            "description": "\u5217\u660e\u6240\u6709\u53c2\u8003\u6765\u6e90"\n'
        "        }\n"
        "    },\n"
        '    "entities": []\n'
        "}\n"
        "</\u8f93\u51fa\u683c\u5f0f>"
    )


def build_outline_prompt(*, invocation: OutlineInvocation) -> PromptBundle:
    return PromptBundle(
        system_prompt=_build_outline_system_prompt(invocation.now.isoformat()),
        user_prompt=(
            "<\u7528\u6237\u7814\u7a76\u9700\u6c42>\n"
            + json.dumps(
                invocation.requirement_detail.model_dump(
                    mode="json", exclude_none=True
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n</\u7528\u6237\u7814\u7a76\u9700\u6c42>\n\n"
            "<\u4fe1\u606f\u83b7\u53d6\u7ed3\u679c>\n"
            + json.dumps(
                [asdict(source) for source in invocation.formatted_sources],
                ensure_ascii=False,
                indent=2,
            )
            + "\n</\u4fe1\u606f\u83b7\u53d6\u7ed3\u679c>"
        ),
    )


def build_writer_prompt(*, invocation: WriterInvocation) -> PromptBundle:
    outline_payload = {
        "title": invocation.outline.title,
        "sections": [asdict(section) for section in invocation.outline.sections],
        "entities": list(invocation.outline.entities),
    }
    source_payload = [asdict(source) for source in invocation.formatted_sources]
    return PromptBundle(
        system_prompt=f"""
# \u80cc\u666f\u4e0e\u4efb\u52a1
\u73b0\u5728\u662f{invocation.now.isoformat()}\uff0c\u4f60\u662f\u4e00\u4e2a\u8d44\u6df1\u7814\u7a76\u5458\uff0c\u4f60\u8d1f\u8d23\u5229\u7528\u5df2\u83b7\u53d6\u4fe1\u606f\u548c\u4f60\u81ea\u8eab\u7684\u4e16\u754c\u77e5\u8bc6\uff0c\u57fa\u4e8e\u7814\u7a76\u5927\u7eb2\u64b0\u5199\u4e00\u7bc7\u6ee1\u8db3\u7528\u6237\u7814\u7a76\u9700\u6c42\u7684\u6df1\u5ea6\u7814\u7a76\u5185\u5bb9\uff08markdown\uff09\u3002

## \u6b63\u6587\u64b0\u5199
- \u4f60\u7684\u5206\u6790\u4e0e\u7814\u7a76\u5e94\u8be5\u6df1\u5165\u7ec6\u81f4\uff0c\u907f\u514d\u76f4\u63a5\u4f7f\u7528\u5df2\u83b7\u53d6\u4fe1\u606f\u4e2d\u7684\u539f\u6587\u3002
- \u7814\u7a76\u8f93\u51fa\u5fc5\u987b\u7d27\u5bc6\u56f4\u7ed5\u7528\u6237\u9700\u6c42\uff0c**\u4fdd\u8bc1\u7814\u7a76\u5185\u5bb9\u524d\u540e\u903b\u8f91\u8fde\u8d2f\u3001\u5408\u7406\u4e14\u6e05\u6670\u3001\u4e0a\u4e0b\u6587\u5b9e\u4f53\u4e00\u81f4\u65e0\u51b2\u7a81\u3002**
- \u4fdd\u8bc1\u6bcf\u4e2a\u7ae0\u8282\u3001\u6bb5\u843d\u4e2d\u7684\u5185\u5bb9\u5145\u5b9e\u6027\u4e0e\u7814\u7a76\u6df1\u5ea6\uff0c\u4e0d\u8981\u5355\u7eaf\u5730\u7f57\u5217\u4fe1\u606f\u6216\u6570\u636e\u3002
- \u6ce8\u610f\uff0c\u9488\u5bf9\u8d2d\u4e70\u63a8\u8350\u7c7b\u9700\u6c42\u5fc5\u987b\u7ed9\u51fa\u5177\u4f53\u7684\u8d2d\u4e70\u5efa\u8bae\u548c\u53c2\u8003\u4ef7\u683c\u3002
- \u63d0\u4f9b\u7684\u53c2\u8003\u4fe1\u606f\u4e2d\u7684\u6bcf\u6761\u4fe1\u606f\u90fd\u5df2\u901a\u8fc7[ref_n]\u7684\u65b9\u5f0f\u7f16\u53f7\uff0c\u4f60\u9700\u8981\u5728\u6b63\u786e\u3001\u5408\u7406\u7684\u4f4d\u7f6e\u6839\u636e\u5b9e\u9645\u4f7f\u7528\u7684\u53c2\u8003\u4fe1\u606f\u521b\u5efa\u811a\u6ce8\u53c2\u8003\u3002
- \u5728\u8f93\u51fa\u672b\u5c3e\u6dfb\u52a0\u811a\u6ce8\uff0c\u4fdd\u8bc1\u5bf9\u5e94\u5173\u7cfb\u6b63\u786e\u3002
- **\uff01\u91cd\u8981\uff01\u7edd\u5bf9\u4e0d\u8981\u8d85\u8fc7\u4e00\u4e07\u5b57\uff01**\u3002

## \u8ba1\u7b97\u4e0e\u56fe\u8868
\u5982\u679c\u9700\u8981\u8fdb\u884c\u6570\u5b66\u8ba1\u7b97\u3001\u5206\u6790\u6216\u56fe\u8868\u7ed8\u5236\uff0c\u8bf7\u4f7f\u7528 `python_interpreter` \u5de5\u5177
- \u56fe\u8868\u7ed8\u5236\u5b8c\u6210\u540e\uff0c\u4f9d\u636e\u771f\u5b9e\u521b\u5efa\u7684\u56fe\u7247\u4fe1\u606f\uff0c\u5728\u8f93\u51fa\u4e2d\u6b63\u786e\u7684\u4f4d\u7f6e\u6dfb\u52a0 markdown \u56fe\u7247\u5f15\u7528

## \u8f93\u51fa
\u4ee5 markdown \u683c\u5f0f\u76f4\u63a5\u8f93\u51fa\u5168\u6587\u3002
""".strip(),
        user_prompt=f"""
<\u53c2\u8003\u4fe1\u606f>
{json.dumps(source_payload, ensure_ascii=False, indent=2)}
</\u53c2\u8003\u4fe1\u606f>

<\u7814\u7a76\u9700\u6c42>
{json.dumps(invocation.requirement_detail.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2)}
</\u7814\u7a76\u9700\u6c42>

<\u5927\u7eb2\u4e0e\u5b9e\u4f53\u7ea6\u675f>
{json.dumps(outline_payload, ensure_ascii=False, indent=2)}
</\u5927\u7eb2\u4e0e\u5b9e\u4f53\u7ea6\u675f>
""".strip(),
    )
