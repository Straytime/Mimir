# Mimir E2B Template

This template extends the default E2B Code Interpreter image with a controlled
`Noto Sans CJK SC` font asset so `python_interpreter` can render Chinese charts
without runtime font installation.

Suggested build flow from the repository root:

```bash
cd services/api
e2b template build \
  -d e2b_template/e2b.Dockerfile \
  -n mimir-code-interpreter-cjk \
  -c "/root/.jupyter/start-up.sh"
```

After the template is published, set `MIMIR_E2B_TEMPLATE=<published-template>`
for the real E2B adapter.
