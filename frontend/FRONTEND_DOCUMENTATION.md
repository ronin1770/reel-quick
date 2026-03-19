# Frontend Documentation (PDF-Ready)

This document summarizes the Next.js frontend for the Instagram Reel creation project. It is structured for easy PDF export.

## Frontend technology

- **Next.js 16 (App Router)** – React framework and routing in `frontend/app`.
- **React 19** – UI rendering.
- **TypeScript** – type safety in `.tsx` components.
- **Tailwind CSS v4** – utility styling via `@import "tailwindcss";` in `frontend/app/globals.css`.
- **Next/font (Google fonts)** – Space Grotesk and Oxanium loaded in `frontend/app/layout.tsx`.
- **ESLint** – linting with `eslint-config-next`.

## Why we selected this technology (rationale)

- **Next.js** provides fast local dev, built-in routing, image optimization, and production-ready builds.
- **React** gives a composable UI model for the video workflow screens.
- **TypeScript** reduces runtime errors in a state-heavy UI (file uploads, timelines, and queues).
- **Tailwind** speeds up UI iteration and enables a consistent design system in CSS.

## Key prerequisites (system + tooling)

- **Node.js (LTS recommended)** and **npm** (or pnpm/yarn/bun).
- Backend API running and reachable (default `http://127.0.0.1:8000`).
- A `.env` or local environment variable for `NEXT_PUBLIC_API_BASE_URL` if the backend is not local.

### Required/expected environment variables

- `NEXT_PUBLIC_API_BASE_URL` – base URL for the backend API.
  - Default fallback in the code: `http://127.0.0.1:8000`.

## Key npm packages

Runtime dependencies in `frontend/package.json`:
- `next`
- `react`
- `react-dom`

Dev dependencies (tooling):
- `typescript`
- `eslint`, `eslint-config-next`
- `tailwindcss`, `@tailwindcss/postcss`
- `@types/node`, `@types/react`, `@types/react-dom`

## package.json status

`frontend/package.json` matches what is imported in the codebase:
- Next.js/React/TypeScript are used directly.
- Tailwind is configured via PostCSS and used in `globals.css`.
- No additional runtime libraries are referenced in the UI code.

## Frontend routes and API calls

### Routes

- `/` – marketing/overview page (`frontend/app/page.tsx`).
- `/create_video` – reel creation workflow (`frontend/app/create_video/page.tsx`).

### API calls used by the frontend

All API calls are made from `/create_video`:

- `POST /uploads` – upload video files (multipart form).
- `POST /videos` – create a video record.
- `POST /video-parts` – create video parts for the reel.
- `POST /videos/{video_id}/enqueue` – enqueue the video for background processing.

## PDF generation (optional)

If you want to export this file to PDF, use:

```bash
pandoc frontend/FRONTEND_DOCUMENTATION.md -o frontend/FRONTEND_DOCUMENTATION.pdf
```
