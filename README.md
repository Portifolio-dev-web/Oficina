# Oficina Fácil

Aplicação web para agendamento e acompanhamento de serviços automotivos.

- **Frontend:** React 19 + Tailwind + Framer Motion (`frontend/`)
- **Backend:** FastAPI com armazenamento em memória (`backend/`)

## Executando com Docker

```bash
docker compose up -d --build
```

- Aplicação: http://localhost:3000
- API: http://localhost:8000/api

## Configuração

As variáveis de ambiente estão documentadas em `backend/.env.example` e `frontend/.env.example`.
Copie para `.env` e ajuste conforme o ambiente. No Docker, elas podem ser definidas em um `.env` na raiz do projeto.

| Variável | Padrão | Descrição |
|---|---|---|
| `ADMIN_USERNAME` | `admin` | Usuário do painel `/admin` |
| `ADMIN_EMAIL` | — | E-mail aceito como login alternativo |
| `ADMIN_PASSWORD` | — | Senha do painel admin — defina a sua no `backend/.env` local, nunca aqui |
| `CORS_ORIGINS` | `*` | Origens permitidas, separadas por vírgula |
| `REACT_APP_BACKEND_URL` | vazio | URL base da API usada pelo frontend |

## Executando localmente

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

Frontend:

```bash
cd frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8000 yarn start
```

## Testes

Com o backend rodando:

```bash
cd backend
pytest
```

Use `API_BASE_URL` para apontar os testes para outro endereço.

## Observações

- Os dados ficam no Supabase/Postgres do projeto configurado (ver `supabase_schema.sql`), não em memória.
- O código de verificação do cadastro/login (OTP) é enviado de verdade pelo provedor de SMS configurado no Supabase Auth (Authentication > Providers > Phone). Para testar sem gastar SMS real, cadastre um "Test phone number" lá e preencha `TEST_OTP_PHONE`/`TEST_OTP_CODE` no `.env`.
- As notificações de mudança de status do agendamento são simuladas por padrão (só vão para o log do backend) — para enviá-las de verdade, preencha `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`/`TWILIO_FROM_NUMBER` no `backend/.env` (ver comentários em `backend/.env.example`).
