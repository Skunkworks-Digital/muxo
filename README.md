# MuxoSMS

Monorepo for experimental SMS gateway with FastAPI backend and React UI.

## Backend

- Python 3.11 + FastAPI
- Run: `uvicorn backend.main:app`

## UI

- Vite + React + TypeScript
- From `ui` directory run: `npm run dev`

## Development

Install pre-commit hooks:

```bash
pre-commit install
```

Run lint checks:

```bash
pre-commit run --files <files>
npm run lint --prefix ui
```
