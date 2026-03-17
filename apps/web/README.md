# apps/web

Next.js App Router frontend for Mimir.

## Local commands

```bash
pnpm dev
pnpm build
pnpm start
pnpm typecheck
pnpm lint
pnpm test:unit
pnpm test:contract
pnpm test:component
pnpm test:integration
pnpm test:e2e
```

## Runtime contract

- 浏览器直连后端 API 与 SSE，不引入 Next.js BFF。
- 本地开发读取 [`.env.local.example`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/.env.local.example) 中的 `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`。
- 生产部署到 Vercel 时，必须在项目环境变量中显式设置 `NEXT_PUBLIC_API_BASE_URL` 指向 Railway API 基址。

## Deploy contract

- Deployment target: `Vercel`
- Root Directory: `apps/web`
- Config file: [`vercel.json`](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/apps/web/vercel.json)
- Build command: `pnpm build`
- Runtime: Vercel 默认 Next.js 运行时

完整 env matrix 与后端联动约束见 [docs/Deploy_Contract.md](/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/docs/Deploy_Contract.md)。
