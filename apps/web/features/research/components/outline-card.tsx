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
      className="bg-surface-container px-6 py-6 outline outline-1 outline-outline-variant/15"
    >
      <div className="grid gap-5">
        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr),auto] md:items-start">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <p className="text-[10px] font-ui font-semibold uppercase tracking-[0.18em] text-tertiary">
                Outline
              </p>
              <span aria-hidden="true" className="h-px w-8 bg-primary opacity-60" />
            </div>
            <h3 className="max-w-[20ch] text-[22px] font-narrative font-semibold leading-tight text-white">
              {outline.title}
            </h3>
            <p className="text-[10px] font-ui uppercase tracking-[0.18em] text-secondary">
              Structured reading path before report delivery
            </p>
          </div>

          <div className="bg-surface-container-lowest px-4 py-4 outline outline-1 outline-outline-variant/15">
            <p className="text-[10px] font-ui font-semibold uppercase tracking-[0.18em] text-tertiary">
              Sections
            </p>
            <p className="mt-3 text-[30px] font-ui font-semibold leading-none text-white">
              {fmt02(orderedSections.length)}
            </p>
          </div>
        </div>

        <ol aria-label="章节序列" className="grid gap-3">
          {orderedSections.map((section, index) => {
            const sectionIndex = section.order > 0 ? section.order : index + 1;
            const label = fmt02(sectionIndex);

            return (
              <li
                className="bg-surface-container-lowest px-4 py-4 outline outline-1 outline-outline-variant/15"
                key={section.section_id}
              >
                <div className="grid gap-4 md:grid-cols-[auto,minmax(0,1fr)] md:items-center">
                  <div className="bg-surface-container-low px-3 py-3">
                    <p className="text-[10px] font-ui font-semibold uppercase tracking-[0.18em] text-tertiary">
                      Section {label}
                    </p>
                    <p className="mt-2 text-[24px] font-ui font-semibold leading-none text-white">
                      {label}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <p className="text-[10px] font-ui font-semibold uppercase tracking-[0.18em] text-tertiary">
                      Ordered title
                    </p>
                    <h4 className="text-[18px] font-narrative font-semibold leading-tight text-white">
                      {section.title}
                    </h4>
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
