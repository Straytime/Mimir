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

  const orderedSections = [...outline.sections].sort((left, right) => {
    return left.order - right.order;
  });

  return (
    <section
      aria-label="报告大纲"
      className="bg-surface-container-low px-6 py-6"
    >
      <div className="grid gap-6">
        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr),auto] md:items-start">
          <div className="space-y-2">
            <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
              Outline
            </p>
            <h3 className="text-[22px] font-narrative font-semibold leading-tight text-primary">
              {outline.title}
            </h3>
            <p className="text-[11px] font-ui uppercase tracking-[0.15em] text-secondary">
              Structured reading path before report delivery
            </p>
          </div>

          <div className="bg-surface-container-high px-4 py-4">
            <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
              Sections
            </p>
            <p className="mt-2 text-[28px] font-ui font-semibold leading-none text-primary">
              {fmt02(orderedSections.length)}
            </p>
          </div>
        </div>

        <ol aria-label="章节序列" className="grid gap-4">
          {orderedSections.map((section, index) => {
            const sectionIndex = section.order > 0 ? section.order : index + 1;
            const label = fmt02(sectionIndex);

            return (
              <li
                className="bg-surface-container-high px-4 py-4"
                key={section.section_id}
              >
                <div className="grid gap-4 md:grid-cols-[auto,minmax(0,1fr)] md:items-start">
                  <div className="bg-surface-container-lowest px-3 py-3">
                    <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
                      Section
                    </p>
                    <p className="mt-2 text-[28px] font-ui font-semibold leading-none text-primary">
                      {label}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-secondary">
                      章节 {label} / Report Flow
                    </p>
                    <h4 className="text-[20px] font-narrative font-semibold leading-tight text-primary">
                      {section.title}
                    </h4>
                    {section.description ? (
                      <p className="max-w-[58ch] text-sm font-narrative leading-7 text-secondary">
                        {section.description}
                      </p>
                    ) : null}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
