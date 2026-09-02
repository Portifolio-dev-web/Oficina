# PRD — AutoFix Pro: Automotive Repair Shop Scheduling & Tracking

## Original Problem Statement
Complete automotive repair shop scheduling and tracking web app (pt-BR) with mock OTP onboarding (phone + SMS simulation), smart vehicle brand→model select, service catalog with 3 categories and booking wizard (calendar + Manhã/Tarde slots), live 5-stage tracking stepper at /rastreio/[id], floating Dev/Demo control bar, simulated SMS feed with timestamps. Dark slate theme, emerald/amber status badges, Framer Motion animations, zero external SMS credentials.

## Architecture Decision (deviation from spec)
Spec requested Next.js App Router + Route Handlers. The environment runs React (port 3000) + FastAPI (port 8001), so Route Handlers were mapped 1:1 to FastAPI endpoints with identical contracts (`/api/auth/send-otp`, `/api/auth/verify-otp`, `/api/vehicles/models`, `/api/appointments`, `/api/tracking/{id}`) backed by an in-memory mock store (per spec's mock strategy). Frontend uses React Router + Framer Motion + lucide-react.

## User Personas
- Vehicle owner (pt-BR): registers with phone OTP, books services, tracks repair live.
- Tester/Demo user: uses floating control bar to advance stages and watch SMS feed.

## Core Requirements (static)
- OTP registration: 6 split inputs, auto-advance, paste, 60s countdown, SMS toast `[Simulação SMS] Seu código é: 123456`
- Booking: 3 service categories, selectable cards, calendar, Manhã/Tarde slots, confirmation SMS
- Tracking: 5-stage stepper, stage badges, SMS feed tab, demo advance/regress/reset

## Implemented (2026-06)
- Backend: full mock API in `/app/backend/server.py` (in-memory stores, fixed OTP 123456, stage-based SMS templates, status advance/jump with clamping)
- Frontend: Home landing, OnboardingModal (form + OTP), Booking wizard (/agendar) with MiniCalendar + time slots + sticky summary bar, Tracking (/rastreio/:id) with animated stepper, SMS feed tab, DevControlBar
- Testing: 10/10 backend pytest + full E2E Playwright pass (iteration_1.json, 100% success)
- Admin dashboard (/admin): GET /api/admin/overview (KPIs: em manutenção, aguardando, prontos, mecânicos disponíveis X/Y, serviços agendados), vehicle cards with advance/regress stage (fires simulated SMS toast), mechanics team with availability toggle (POST /api/admin/mechanics/{id}/toggle), services agenda with count + average duration; seed_demo() spawns 6 demo appointments (AF-DEMO01..06) + 5 mechanics on empty store; navbar 'Painel Oficina' link
- Testing iteration_2.json: admin feature 100% backend (5 pytest) + frontend E2E

## Known Limitations
- In-memory store resets on backend restart (per spec mock strategy)
- SMS is intentionally simulated (toast + per-order SMS log)
- Brand/model selects use native <select> elements
- Admin panel has no auth guard (demo panel — needs protection for production)

## Backlog
- P0: Auth guard for /admin (admin login)
- P1: Persist appointments in MongoDB; login (returning user) flow using stored password; assign mechanics to service orders
- P2: Multiple vehicles per user; real SMS via Twilio; appointment cancellation/rescheduling; workload/capacity indicators per mechanic

## Next Tasks
- Await user review; then consider admin auth + persistence + real notifications
