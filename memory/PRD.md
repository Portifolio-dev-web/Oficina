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
- Admin dashboard (/admin): protegido por login (POST /api/admin/login, Bearer token em memória; guard `require_admin` em overview/toggle; POST /api/admin/logout invalida token). Credenciais fixas no código: usuário `admin` (ou e-mail `monitor.informatica25@gmail.com`) / senha `admin@2043`. Frontend: tela de login (localStorage `autofix_admin`), botão 'Sair do painel', 401 redireciona ao login.
- Admin overview: GET /api/admin/overview (KPIs: em manutenção, aguardando, prontos, mecânicos disponíveis X/Y, serviços agendados), vehicle cards com advance/regress (SMS simulado), equipe com toggle (POST /api/admin/mechanics/{id}/toggle), agenda de serviços; seed_demo() com 6 agendamentos (AF-DEMO01..06) + 5 mecânicos; navbar 'Painel Oficina'
- Testing: iteration_2.json (admin 100%), iteration_3.json (admin auth 16/16 pytest + E2E, regressão pública OK)

## Known Limitations
- In-memory store resets on backend restart (per spec mock strategy); tokens admin também são invalidados no restart
- SMS is intentionally simulated (toast + per-order SMS log)
- Credenciais admin fixas no código por decisão do usuário — para produção mover para env vars + hash

## Backlog
- P0: (resolvido) Auth guard para /admin
- P1: Persist appointments in MongoDB; login (returning user) flow usando senha do cliente; assign mechanics to service orders
- P2: Multiple vehicles per user; real SMS via Twilio; appointment cancellation/rescheduling; capacity indicators per mechanic

## Next Tasks
- Await user review; considerar persistência MongoDB + SMS real
