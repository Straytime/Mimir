import { useResearchSessionStore } from "../providers/research-workspace-providers";

export function OutlineCard() {
  const outline = useResearchSessionStore((state) => state.stream.outline);
  const outlineReady = useResearchSessionStore(
    (state) => state.stream.outlineReady,
  );

  if (!outline || !outlineReady) {
    return null;
  }

  return (
    <section
      aria-label="报告大纲"
      className="bg-surface-container-low p-6"
    >
      <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
        Outline
      </p>
      <h3 className="mt-sp-2 text-lg font-narrative font-semibold text-primary">
        {outline.title}
      </h3>
      <ol className="mt-4 space-y-2">
        {outline.sections.map((section) => (
          <li
            key={section.section_id}
            className="text-sm font-narrative text-primary"
          >
            {section.title}
          </li>
        ))}
      </ol>
    </section>
  );
}
