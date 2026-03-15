"use client";

export function ResearchPageClient() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-6 py-16">
      <div className="space-y-4">
        <p className="text-sm font-medium uppercase tracking-[0.24em] text-sky-700">
          Mimir
        </p>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-950">
          Mimir Frontend Stage 0 Harness
        </h1>
        <p className="max-w-2xl text-base leading-7 text-slate-700">
          This shell verifies the Next.js App Router, test harness, and Playwright
          baseline without entering the research workflow implementation.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-3xl border border-slate-200/70 bg-white/70 p-6 shadow-sm backdrop-blur">
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            App Router
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            A minimal client component is mounted from <code>app/page.tsx</code>.
          </p>
        </article>

        <article className="rounded-3xl border border-slate-200/70 bg-white/70 p-6 shadow-sm backdrop-blur">
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            Test Harness
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            Vitest, jsdom, Testing Library, shared fixtures, and scripted SSE are wired.
          </p>
        </article>

        <article className="rounded-3xl border border-slate-200/70 bg-white/70 p-6 shadow-sm backdrop-blur">
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            Playwright
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            The browser baseline uses a lightweight mock API server with a health route.
          </p>
        </article>
      </section>
    </main>
  );
}
