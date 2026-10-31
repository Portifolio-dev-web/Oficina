-- =============================================================================
-- OFICINA FÁCIL — SEED DE CATÁLOGO
-- =============================================================================
-- Roda DEPOIS de supabase_schema.sql. Popula os catálogos públicos que antes
-- viviam como dados fixos em Python (VEHICLE_MODELS, SERVICE_CATEGORIES e
-- MECHANICS em backend/server.py e frontend/src/constants/data.js) para que
-- o backend passe a ler tudo do Postgres.
--
-- Não inclui dados de demonstração de agendamentos (AF-DEMO01..06): como
-- bookings.customer_id referencia profiles -> auth.users, esses registros
-- exigem usuários reais do Supabase Auth e por isso são criados via
-- backend/scripts/seed_demo.py (que usa a Admin API), não por SQL puro.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Marcas e modelos de veículo (espelha VEHICLE_MODELS)
-- -----------------------------------------------------------------------------
insert into public.vehicle_makes (name) values
  ('Chevrolet'), ('Toyota'), ('Volkswagen'), ('Fiat'), ('Honda'),
  ('Hyundai'), ('Ford'), ('Renault'), ('Nissan'), ('Jeep')
on conflict (name) do nothing;

insert into public.vehicle_models (make_id, name)
select m.id, model
from public.vehicle_makes m
join (values
  ('Chevrolet', 'Onix'), ('Chevrolet', 'Onix Plus'), ('Chevrolet', 'Tracker'),
  ('Chevrolet', 'S10'), ('Chevrolet', 'Spin'), ('Chevrolet', 'Cruze'),

  ('Toyota', 'Corolla'), ('Toyota', 'Corolla Cross'), ('Toyota', 'Hilux'),
  ('Toyota', 'Yaris'), ('Toyota', 'SW4'),

  ('Volkswagen', 'Gol'), ('Volkswagen', 'Polo'), ('Volkswagen', 'T-Cross'),
  ('Volkswagen', 'Virtus'), ('Volkswagen', 'Nivus'), ('Volkswagen', 'Saveiro'),

  ('Fiat', 'Argo'), ('Fiat', 'Mobi'), ('Fiat', 'Toro'), ('Fiat', 'Strada'), ('Fiat', 'Pulse'),

  ('Honda', 'Civic'), ('Honda', 'City'), ('Honda', 'HR-V'), ('Honda', 'Fit'),

  ('Hyundai', 'HB20'), ('Hyundai', 'HB20S'), ('Hyundai', 'Creta'), ('Hyundai', 'Tucson'),

  ('Ford', 'Ka'), ('Ford', 'EcoSport'), ('Ford', 'Ranger'), ('Ford', 'Fiesta'),

  ('Renault', 'Kwid'), ('Renault', 'Sandero'), ('Renault', 'Logan'), ('Renault', 'Duster'),

  ('Nissan', 'Kicks'), ('Nissan', 'Versa'), ('Nissan', 'Frontier'),

  ('Jeep', 'Renegade'), ('Jeep', 'Compass'), ('Jeep', 'Commander')
) as v(make, model) on v.make = m.name
on conflict (make_id, name) do nothing;


-- -----------------------------------------------------------------------------
-- Categorias e catálogo de serviços (espelha SERVICE_CATEGORIES)
-- price_cents = preço em reais * 100; duration_minutes convertido dos
-- rótulos textuais originais ("45 min", "1 h 30", "2 h", ...).
-- -----------------------------------------------------------------------------
insert into public.service_categories (id, label, sort_order) values
  ('preventiva', 'Manutenção Preventiva', 1),
  ('reparacao', 'Reparação e Correção', 2),
  ('diagnostico', 'Diagnóstico e Elétrica', 3)
on conflict (id) do nothing;

insert into public.services (id, category_id, name, description, price_cents, duration_minutes, icon) values
  ('troca-oleo', 'preventiva', 'Troca de óleo e filtros', 'Óleo sintético + filtros de óleo e ar', 18900, 45, 'droplets'),
  ('troca-fluidos', 'preventiva', 'Troca de fluidos', 'Freio, arrefecimento e direção hidráulica', 24900, 60, 'waves'),
  ('revisao-periodica', 'preventiva', 'Revisão periódica', 'Checklist completo de 40 itens', 39900, 120, 'clipboard'),

  ('freios', 'reparacao', 'Sistema de freios', 'Pastilhas, discos e fluido de freio', 45900, 90, 'disc'),
  ('suspensao', 'reparacao', 'Suspensão e direção', 'Amortecedores, buchas e terminais', 68900, 150, 'cog'),
  ('alinhamento', 'reparacao', 'Alinhamento e balanceamento', 'Alinhamento 3D + balanceamento das 4 rodas', 15900, 50, 'gauge'),
  ('motor-transmissao', 'reparacao', 'Motor e transmissão', 'Diagnóstico e reparo de motor e câmbio', 129000, 240, 'wrench'),

  ('diag-eletronico', 'diagnostico', 'Diagnóstico eletrônico', 'Scanner OBD + leitura de falhas', 14900, 40, 'cpu'),
  ('eletrica-geral', 'diagnostico', 'Elétrica geral', 'Bateria, alternador, chicote e iluminação', 28900, 90, 'zap'),
  ('climatizacao', 'diagnostico', 'Climatização', 'Ar-condicionado: gás, filtros e higienização', 34900, 80, 'snowflake')
on conflict (id) do nothing;


-- -----------------------------------------------------------------------------
-- Equipe de mecânicos (espelha MECHANICS)
-- -----------------------------------------------------------------------------
insert into public.mechanics (name, specialty, available) values
  ('Carlos Souza', 'Motor e transmissão', true),
  ('Rafael Lima', 'Freios e suspensão', true),
  ('Bruno Alves', 'Elétrica e diagnóstico', false),
  ('Diego Ferreira', 'Climatização', true),
  ('André Santos', 'Revisão geral', false);


-- =============================================================================
-- FIM DO SEED
-- =============================================================================
