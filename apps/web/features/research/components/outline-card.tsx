import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { fmt02 } from "../utils/format";

export function OutlineCard() {
  const outline = useResearchSessionStore((state) => state.stream.outline);
  const outlineReady = useResearchSessionStore(
    (state) => state.stream.outlineReady,
  );

  if (!outline || !outlineReady) {
    return null;
  }

  if (outline.sections.length === 0) {
    return null;
  }

  const orderedSections = [...outline.sections].sort((left, right) => {
    return left.order - right.order;
  });

  return (
    <section
      aria-label="报告大纲"
      className="bg-surface-container px-5 py-5"
    >
      <div className="grid gap-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <p className="text-[10px] font-ui font-semibold uppercase tracking-[0.18em] text-tertiary">
                Outline
              </p>
              <span aria-hidden="true" className="h-[5px] w-[5px] bg-primary opacity-70" />
            </div>
            <h3 className="max-w-[24ch] text-[20px] font-narrative font-semibold leading-tight text-white">
              {outline.title}
            </h3>
          </div>

          <p className="pt-0.5 text-[10px] font-ui uppercase tracking-[0.18em] text-secondary opacity-70">
            {fmt02(orderedSections.length)} sections
          </p>
        </div>

        <ol aria-label="章节序列" className="grid gap-2.5">
          {orderedSections.map((section, index) => {
            const sectionIndex = section.order > 0 ? section.order : index + 1;
            const label = fmt02(sectionIndex);

            return (
              <li className="bg-surface-container-low px-3 py-3" key={section.section_id}>
                <div className="grid grid-cols-[auto,minmax(0,1fr)] items-start gap-3">
                  <p className="pt-[0.15rem] text-[11px] font-ui font-semibold uppercase tracking-[0.18em] text-tertiary">
                    {label}
                  </p>
                  <h4 className="text-[16px] font-narrative font-semibold leading-[1.35] text-white">
                    {section.title}
                  </h4>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
