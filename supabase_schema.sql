-- =============================================================================
-- OFICINA FÁCIL — SCHEMA POSTGRESQL OTIMIZADO PARA SUPABASE
-- =============================================================================
-- Este schema foi derivado da análise do código-fonte atual do projeto:
--   - backend/server.py        -> entidades reais: OTP/USERS, APPOINTMENTS,
--                                  VEHICLE_MODELS, MECHANICS, STAGES, admin auth
--   - frontend/src/pages/{Admin,Booking,Tracking}.jsx
--   - frontend/src/constants/data.js -> SERVICE_CATEGORIES, TIME_SLOTS, STAGES
--   - frontend/src/components/OnboardingModal.jsx -> cadastro cliente (OTP + senha + veículo)
--
-- DECISÃO DE MODELAGEM — AUTENTICAÇÃO:
--   O mock atual usa um fluxo próprio (telefone + OTP fixo "123456" para
--   clientes; usuário/senha fixos em código para admin). Para rodar em
--   Supabase de forma segura e aproveitar RLS baseada em auth.uid(), este
--   schema assume a migração de AMBOS os perfis (cliente e admin) para o
--   Supabase Auth (auth.users), com uma tabela `profiles` 1:1 estendendo o
--   usuário autenticado e guardando o campo `role`. Isso é o padrão
--   recomendado pelo Supabase e é o que permite que as políticas de RLS
--   abaixo funcionem sem reimplementar autenticação na mão.
--
-- DECISÃO DE MODELAGEM — CHAVES PRIMÁRIAS:
--   - Tabelas sem identificador "visível" fora do sistema (profiles, vehicles,
--     mechanics, booking_services, booking_status_history) usam UUID.
--   - Tabelas cujo identificador atual já aparece em URLs, testids ou é usado
--     como slug estável no código (bookings -> "AF-XXXXXX" usado em
--     /rastreio/:id; services -> "troca-oleo"; service_categories ->
--     "preventiva") usam TEXT como chave primária, preservando compatibilidade
--     1:1 com o contrato atual da API/frontend e facilitando a migração dos
--     dados do mock in-memory para o Postgres.
-- =============================================================================


-- =============================================================================
-- 0. EXTENSÕES
-- =============================================================================
-- gen_random_uuid() já é nativo a partir do Postgres 13 (base do Supabase),
-- mas habilitamos pgcrypto explicitamente por portabilidade/clareza.
create extension if not exists "pgcrypto";


-- =============================================================================
-- 1. FUNÇÃO E TRIGGER GENÉRICOS DE updated_at
-- =============================================================================
-- Function genérica: qualquer tabela com coluna `updated_at` pode reutilizá-la.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

comment on function public.set_updated_at() is
  'Function genérica usada por triggers BEFORE UPDATE para manter updated_at sincronizado em qualquer tabela.';


-- =============================================================================
-- 2. PERFIS (clientes e administradores)
-- =============================================================================
-- Estende auth.users (1:1). O telefone é o identificador de negócio usado
-- hoje no fluxo de OTP (USERS dict, chave = phone, no backend atual).
-- `role` define o nível de acesso usado nas policies de RLS mais abaixo.
create table public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  role        text not null default 'cliente' check (role in ('cliente', 'admin')),
  name        text not null default '',
  phone       text unique,                     -- ex.: "(11) 99999-8888" — login do cliente hoje
  email       text unique,                      -- login do admin hoje (ADMIN_EMAIL)
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

comment on table public.profiles is
  'Extensão de auth.users com dados de negócio e papel (cliente/admin). Substitui os dicts USERS e as credenciais fixas de admin do backend atual.';

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Cria automaticamente um profile "cliente" sempre que um novo usuário é
-- criado no Supabase Auth, evitando que o cliente precise (ou consiga) fazer
-- INSERT direto em profiles — isso fecha uma brecha comum de segurança onde
-- o próprio usuário poderia se promover a admin via insert manual.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, name, phone, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'name', ''),
    new.phone,
    new.email
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Helper de autorização: função SECURITY DEFINER para evitar recursão de RLS
-- (uma policy em `profiles` que consultasse `profiles` diretamente entraria
-- em loop de avaliação); roda com privilégios do definidor, ignorando RLS.
create or replace function public.is_admin()
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin'
  );
$$;

comment on function public.is_admin() is
  'Retorna true se o usuário autenticado atual tiver role = admin. SECURITY DEFINER evita recursão de RLS sobre a própria tabela profiles.';


-- =============================================================================
-- 3. CATÁLOGO DE VEÍCULOS (marcas/modelos) — espelha VEHICLE_MODELS do backend
-- =============================================================================
create table public.vehicle_makes (
  id    uuid primary key default gen_random_uuid(),
  name  text not null unique            -- "Chevrolet", "Toyota", ...
);

create table public.vehicle_models (
  id       uuid primary key default gen_random_uuid(),
  make_id  uuid not null references public.vehicle_makes (id) on delete cascade,
  name     text not null,               -- "Onix", "Corolla", ...
  unique (make_id, name)
);

comment on table public.vehicle_makes is 'Catálogo de marcas de veículos, equivalente às chaves de VEHICLE_MODELS em backend/server.py.';
comment on table public.vehicle_models is 'Catálogo de modelos por marca, equivalente aos valores (listas) de VEHICLE_MODELS.';


-- =============================================================================
-- 4. VEÍCULOS DO CLIENTE
-- =============================================================================
create table public.vehicles (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid not null references public.profiles (id) on delete cascade,
  make_id     uuid references public.vehicle_makes (id),
  model_id    uuid references public.vehicle_models (id),
  -- make/model em texto livre: o cadastro (OnboardingModal) permite digitar
  -- marca/modelo fora do catálogo fixo, então mantemos texto como fonte da
  -- verdade para exibição e os FKs acima como enriquecimento opcional.
  make        text not null,
  model       text not null,
  plate       text,                     -- opcional no cadastro atual ("Placa (opcional)")
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create unique index vehicles_plate_unique_idx on public.vehicles (plate) where plate is not null;
create index vehicles_owner_id_idx on public.vehicles (owner_id);

comment on table public.vehicles is
  'Veículos cadastrados pelo cliente. plate é opcional (reflete o formulário de onboarding) mas único quando informado.';

create trigger vehicles_set_updated_at
  before update on public.vehicles
  for each row execute function public.set_updated_at();


-- =============================================================================
-- 5. CATÁLOGO DE SERVIÇOS — espelha SERVICE_CATEGORIES em frontend/src/constants/data.js
-- =============================================================================
create table public.service_categories (
  id     text primary key,              -- "preventiva", "reparacao", "diagnostico"
  label  text not null,                 -- "Manutenção Preventiva", ...
  sort_order smallint not null default 0
);

create table public.services (
  id           text primary key,        -- slug, ex.: "troca-oleo", "freios"
  category_id  text not null references public.service_categories (id),
  name         text not null,
  description  text not null default '',
  price_cents  integer not null check (price_cents >= 0),  -- valores monetários em centavos
  duration_minutes integer not null check (duration_minutes > 0),
  icon         text,
  active       boolean not null default true,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

comment on table public.service_categories is 'Categorias da vitrine de serviços (abas do fluxo de agendamento).';
comment on table public.services is
  'Catálogo de serviços oferecidos pela oficina, com preço e duração padrão. price_cents evita problemas de arredondamento de float em valores monetários.';

create trigger services_set_updated_at
  before update on public.services
  for each row execute function public.set_updated_at();

create index services_category_id_idx on public.services (category_id);


-- =============================================================================
-- 6. MECÂNICOS — espelha MECHANICS no backend
-- =============================================================================
create table public.mechanics (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  specialty   text not null default '',
  available   boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

comment on table public.mechanics is 'Equipe de mecânicos e disponibilidade, usada no painel administrativo (toggle disponível/ocupado).';

create trigger mechanics_set_updated_at
  before update on public.mechanics
  for each row execute function public.set_updated_at();


-- =============================================================================
-- 7. ETAPAS DE RASTREAMENTO — espelha STAGES (backend e frontend)
-- =============================================================================
-- Tabela de apoio (lookup) em vez de enum fixo: permite editar os textos das
-- etapas sem precisar de migração de schema, mantendo a ORDEM (stage_index)
-- como contrato estável consumido pela UI (stepper de 5 etapas).
create table public.tracking_stages (
  stage_index  smallint primary key,
  name         text not null,
  description  text not null
);

insert into public.tracking_stages (stage_index, name, description) values
  (0, 'Agendamento Confirmado',          'Recebemos seu agendamento e reservamos o box.'),
  (1, 'Veículo Recebido na Oficina',     'Check-in realizado e inspeção inicial registrada.'),
  (2, 'Diagnóstico / Em Execução',       'Nossa equipe está trabalhando no seu veículo.'),
  (3, 'Teste de Rodagem / CQ',           'Testes finais e controle de qualidade em andamento.'),
  (4, 'Pronto para Retirada',            'Tudo certo! Seu veículo já pode ser retirado.');

comment on table public.tracking_stages is
  'Lookup fixo das 5 etapas do funil de rastreamento, equivalente ao array STAGES duplicado hoje em backend e frontend.';


-- =============================================================================
-- 8. AGENDAMENTOS (BOOKINGS) — espelha APPOINTMENTS no backend
-- =============================================================================
create table public.bookings (
  id            text primary key
                  default ('AF-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 6))),
  customer_id   uuid not null references public.profiles (id),
  vehicle_id    uuid not null references public.vehicles (id),
  mechanic_id   uuid references public.mechanics (id),      -- atribuição opcional feita pelo admin
  scheduled_date date not null,
  scheduled_time time not null,
  period        text not null default '' check (period in ('', 'Manhã', 'Tarde')),
  stage_index   smallint not null default 0 references public.tracking_stages (stage_index),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

comment on table public.bookings is
  'Agendamentos de serviço. id segue o formato "AF-XXXXXX" já usado nas URLs de rastreamento (/rastreio/:id) do frontend atual.';

create trigger bookings_set_updated_at
  before update on public.bookings
  for each row execute function public.set_updated_at();

create index bookings_customer_id_idx on public.bookings (customer_id);
create index bookings_vehicle_id_idx on public.bookings (vehicle_id);
create index bookings_scheduled_date_idx on public.bookings (scheduled_date);
create index bookings_stage_index_idx on public.bookings (stage_index);


-- =============================================================================
-- 9. SERVIÇOS DE UM AGENDAMENTO (N:N bookings <-> services)
-- =============================================================================
-- Guardamos "snapshot" de nome/preço/duração no momento do agendamento, para
-- que alterações futuras no catálogo (services) não reescrevam o histórico
-- financeiro de agendamentos já criados.
create table public.booking_services (
  id               uuid primary key default gen_random_uuid(),
  booking_id       text not null references public.bookings (id) on delete cascade,
  service_id       text not null references public.services (id),
  service_name     text not null,
  price_cents      integer not null check (price_cents >= 0),
  duration_minutes integer not null check (duration_minutes > 0),
  created_at       timestamptz not null default now(),
  unique (booking_id, service_id)
);

comment on table public.booking_services is
  'Itens de serviço de um agendamento, com snapshot de nome/preço/duração no momento da contratação (equivalente à lista "services" dentro de cada appointment no mock).';

create index booking_services_booking_id_idx on public.booking_services (booking_id);


-- =============================================================================
-- 10. HISTÓRICO DE RASTREAMENTO / SMS — espelha appointment["smsLogs"]
-- =============================================================================
create table public.booking_status_history (
  id           uuid primary key default gen_random_uuid(),
  booking_id   text not null references public.bookings (id) on delete cascade,
  stage_index  smallint not null references public.tracking_stages (stage_index),
  message      text not null,           -- texto do "SMS" simulado exibido ao cliente
  created_at   timestamptz not null default now()
);

comment on table public.booking_status_history is
  'Linha do tempo de mudanças de etapa de um agendamento (equivalente a smsLogs no mock atual). Cliente só tem SELECT; o INSERT é feito pelo backend/trigger, nunca diretamente pelo cliente (ver seção de RLS).';

create index booking_status_history_booking_id_idx on public.booking_status_history (booking_id);
create index booking_status_history_created_at_idx on public.booking_status_history (booking_id, created_at);

-- Trigger "bônus": sempre que o stage_index de um agendamento muda, registra
-- automaticamente uma entrada no histórico — equivalente ao que o backend
-- Python faz manualmente hoje em update_status()/stage_sms(). Isso garante
-- que a trilha de auditoria não dependa de o código da aplicação lembrar de
-- inserir a linha de histórico.
create or replace function public.log_booking_stage_change()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if (tg_op = 'INSERT') or (new.stage_index is distinct from old.stage_index) then
    insert into public.booking_status_history (booking_id, stage_index, message)
    values (
      new.id,
      new.stage_index,
      (select description from public.tracking_stages where stage_index = new.stage_index)
    );
  end if;
  return new;
end;
$$;

create trigger bookings_log_stage_change
  after insert or update on public.bookings
  for each row execute function public.log_booking_stage_change();

comment on function public.log_booking_stage_change() is
  'Registra automaticamente uma entrada em booking_status_history na criação do agendamento e em toda troca de stage_index. SECURITY DEFINER para poder inserir mesmo sob RLS restritiva.';


-- =============================================================================
-- 11. ROW LEVEL SECURITY (RLS)
-- =============================================================================
-- Regra geral pedida:
--   - Clientes: leem e criam apenas os PRÓPRIOS agendamentos/rastreamentos.
--   - Admin (role = 'admin'): acesso total a todas as tabelas.
-- Catálogos (serviços, categorias, marcas/modelos, mecânicos, etapas) são
-- publicamente legíveis (necessário para montar a tela de agendamento antes
-- do login) e só o admin pode alterá-los.
-- =============================================================================

alter table public.profiles enable row level security;
alter table public.vehicle_makes enable row level security;
alter table public.vehicle_models enable row level security;
alter table public.vehicles enable row level security;
alter table public.service_categories enable row level security;
alter table public.services enable row level security;
alter table public.mechanics enable row level security;
alter table public.tracking_stages enable row level security;
alter table public.bookings enable row level security;
alter table public.booking_services enable row level security;
alter table public.booking_status_history enable row level security;

-- ---------------------------------------------------------------------------
-- profiles
-- ---------------------------------------------------------------------------
create policy "profiles_select_own_or_admin"
  on public.profiles for select
  using (id = auth.uid() or public.is_admin());

create policy "profiles_update_own_or_admin"
  on public.profiles for update
  using (id = auth.uid() or public.is_admin())
  with check (id = auth.uid() or public.is_admin());

-- Não há policy de INSERT/DELETE para clientes: o profile nasce via trigger
-- handle_new_user() (SECURITY DEFINER) ao cadastrar em auth.users, então o
-- cliente nunca precisa (nem pode) inserir/apagar sua própria linha direto.
create policy "profiles_admin_all"
  on public.profiles for all
  using (public.is_admin())
  with check (public.is_admin());

-- ---------------------------------------------------------------------------
-- catálogos públicos (leitura liberada, escrita só admin)
-- ---------------------------------------------------------------------------
create policy "vehicle_makes_public_read" on public.vehicle_makes for select using (true);
create policy "vehicle_makes_admin_write" on public.vehicle_makes for all using (public.is_admin()) with check (public.is_admin());

create policy "vehicle_models_public_read" on public.vehicle_models for select using (true);
create policy "vehicle_models_admin_write" on public.vehicle_models for all using (public.is_admin()) with check (public.is_admin());

create policy "service_categories_public_read" on public.service_categories for select using (true);
create policy "service_categories_admin_write" on public.service_categories for all using (public.is_admin()) with check (public.is_admin());

create policy "services_public_read" on public.services for select using (true);
create policy "services_admin_write" on public.services for all using (public.is_admin()) with check (public.is_admin());

create policy "mechanics_public_read" on public.mechanics for select using (true);
create policy "mechanics_admin_write" on public.mechanics for all using (public.is_admin()) with check (public.is_admin());

create policy "tracking_stages_public_read" on public.tracking_stages for select using (true);
create policy "tracking_stages_admin_write" on public.tracking_stages for all using (public.is_admin()) with check (public.is_admin());

-- ---------------------------------------------------------------------------
-- vehicles — cliente só vê/gerencia os próprios veículos
-- ---------------------------------------------------------------------------
create policy "vehicles_select_own_or_admin"
  on public.vehicles for select
  using (owner_id = auth.uid() or public.is_admin());

create policy "vehicles_insert_own_or_admin"
  on public.vehicles for insert
  with check (owner_id = auth.uid() or public.is_admin());

create policy "vehicles_update_own_or_admin"
  on public.vehicles for update
  using (owner_id = auth.uid() or public.is_admin())
  with check (owner_id = auth.uid() or public.is_admin());

create policy "vehicles_delete_admin_only"
  on public.vehicles for delete
  using (public.is_admin());

-- ---------------------------------------------------------------------------
-- bookings — cliente lê e cria apenas os próprios; só admin avança/edita etapa
-- ---------------------------------------------------------------------------
create policy "bookings_select_own_or_admin"
  on public.bookings for select
  using (customer_id = auth.uid() or public.is_admin());

create policy "bookings_insert_own_or_admin"
  on public.bookings for insert
  with check (customer_id = auth.uid() or public.is_admin());

-- Cliente não pode alterar/avançar etapa ou excluir agendamento — isso é
-- responsabilidade exclusiva do painel administrativo (Admin.jsx).
create policy "bookings_update_admin_only"
  on public.bookings for update
  using (public.is_admin())
  with check (public.is_admin());

create policy "bookings_delete_admin_only"
  on public.bookings for delete
  using (public.is_admin());

-- ---------------------------------------------------------------------------
-- booking_services — segue a visibilidade do booking pai
-- ---------------------------------------------------------------------------
create policy "booking_services_select_own_or_admin"
  on public.booking_services for select
  using (
    public.is_admin()
    or exists (
      select 1 from public.bookings b
      where b.id = booking_services.booking_id
        and b.customer_id = auth.uid()
    )
  );

-- Cliente pode inserir os serviços escolhidos APENAS no momento da criação
-- do próprio agendamento (stage_index ainda em "Agendamento Confirmado" = 0).
-- Depois disso, qualquer alteração de itens é responsabilidade do admin.
create policy "booking_services_insert_own_at_creation_or_admin"
  on public.booking_services for insert
  with check (
    public.is_admin()
    or exists (
      select 1 from public.bookings b
      where b.id = booking_services.booking_id
        and b.customer_id = auth.uid()
        and b.stage_index = 0
    )
  );

create policy "booking_services_admin_update_delete"
  on public.booking_services for update using (public.is_admin()) with check (public.is_admin());

create policy "booking_services_admin_delete"
  on public.booking_services for delete using (public.is_admin());

-- ---------------------------------------------------------------------------
-- booking_status_history — cliente só LÊ o rastreamento dos próprios
-- agendamentos; o registro é sempre gerado pela trigger log_booking_stage_change
-- (SECURITY DEFINER), nunca por INSERT direto do cliente. Isso evita que um
-- cliente insira entradas falsas de "SMS"/histórico no próprio rastreamento.
-- ---------------------------------------------------------------------------
create policy "booking_status_history_select_own_or_admin"
  on public.booking_status_history for select
  using (
    public.is_admin()
    or exists (
      select 1 from public.bookings b
      where b.id = booking_status_history.booking_id
        and b.customer_id = auth.uid()
    )
  );

create policy "booking_status_history_admin_write"
  on public.booking_status_history for all
  using (public.is_admin())
  with check (public.is_admin());


-- =============================================================================
-- FIM DO SCHEMA
-- =============================================================================
