export const SERVICE_CATEGORIES = [
  {
    id: "preventiva",
    label: "Manutenção Preventiva",
    testid: "tab-category-preventiva",
    services: [
      { id: "troca-oleo", name: "Troca de óleo e filtros", desc: "Óleo sintético + filtros de óleo e ar", price: 189, duration: "45 min", icon: "droplets" },
      { id: "troca-fluidos", name: "Troca de fluidos", desc: "Freio, arrefecimento e direção hidráulica", price: 249, duration: "60 min", icon: "waves" },
      { id: "revisao-periodica", name: "Revisão periódica", desc: "Checklist completo de 40 itens", price: 399, duration: "2 h", icon: "clipboard" },
    ],
  },
  {
    id: "reparacao",
    label: "Reparação e Correção",
    testid: "tab-category-reparacao",
    services: [
      { id: "freios", name: "Sistema de freios", desc: "Pastilhas, discos e fluido de freio", price: 459, duration: "1 h 30", icon: "disc" },
      { id: "suspensao", name: "Suspensão e direção", desc: "Amortecedores, buchas e terminais", price: 689, duration: "2 h 30", icon: "cog" },
      { id: "alinhamento", name: "Alinhamento e balanceamento", desc: "Alinhamento 3D + balanceamento das 4 rodas", price: 159, duration: "50 min", icon: "gauge" },
      { id: "motor-transmissao", name: "Motor e transmissão", desc: "Diagnóstico e reparo de motor e câmbio", price: 1290, duration: "4 h", icon: "wrench" },
    ],
  },
  {
    id: "diagnostico",
    label: "Diagnóstico e Elétrica",
    testid: "tab-category-diagnostico",
    services: [
      { id: "diag-eletronico", name: "Diagnóstico eletrônico", desc: "Scanner OBD + leitura de falhas", price: 149, duration: "40 min", icon: "cpu" },
      { id: "eletrica-geral", name: "Elétrica geral", desc: "Bateria, alternador, chicote e iluminação", price: 289, duration: "1 h 30", icon: "zap" },
      { id: "climatizacao", name: "Climatização", desc: "Ar-condicionado: gás, filtros e higienização", price: 349, duration: "1 h 20", icon: "snowflake" },
    ],
  },
];

export const TIME_SLOTS = {
  manha: { label: "Manhã", hint: "08:00 - 12:00", slots: ["08:00", "09:00", "10:00", "11:00"] },
  tarde: { label: "Tarde", hint: "13:00 - 18:00", slots: ["13:00", "14:00", "15:00", "16:00", "17:00"] },
};

export const STAGES = [
  { name: "Agendamento Confirmado", desc: "Recebemos seu agendamento e reservamos o box." },
  { name: "Veículo Recebido na Oficina", desc: "Check-in realizado e inspeção inicial registrada." },
  { name: "Diagnóstico / Em Execução", desc: "Nossa equipe está trabalhando no seu veículo." },
  { name: "Teste de Rodagem / CQ", desc: "Testes finais e controle de qualidade em andamento." },
  { name: "Pronto para Retirada", desc: "Tudo certo! Seu veículo já pode ser retirado." },
];

export const formatBRL = (v) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
