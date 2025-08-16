# MuxoSMS

Monorepo for experimental SMS gateway with FastAPI backend and React UI.

## Backend

- Python 3.11 + FastAPI
- Run: `uvicorn backend.main:app`

## UI

- Vite + React + TypeScript
- From `ui` directory run: `npm run dev`

## Website

A static project website is available in the `website/` directory. Open `website/index.html` in a browser for an overview and usage instructions.

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

## Backups

Nightly backups of the SQLite database are written to `backups/` with a timestamped filename.
To restore from a backup:

1. Stop the application.
2. Replace `muxo.db` with the desired backup file:

   ```bash
   cp backups/muxo-<timestamp>.db muxo.db
   ```
3. Start the application again.

Old messages older than 90 days and audit records older than 365 days are purged during the nightly job.
