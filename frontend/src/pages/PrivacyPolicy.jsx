import { Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck } from "lucide-react";

// LGPD (Lei nº 13.709/2018), item L3 da auditoria: política de privacidade
// pública e versionada. Mantenha este texto fiel ao que o sistema realmente
// faz (art. 6º, VI) — ao mudar fornecedor, dado coletado ou finalidade,
// atualize a seção correspondente e a versão abaixo.
const VERSION = "1.0";
const UPDATED_AT = "31/10/2026";

const CONTACT_EMAIL = process.env.REACT_APP_PRIVACY_CONTACT_EMAIL || "privacidade@oficinafacil.com.br";

const Section = ({ title, children }) => (
  <section className="border-t border-slate-800 py-7 first:border-t-0 first:pt-0">
    <h2 className="font-display text-lg font-bold text-slate-100">{title}</h2>
    <div className="mt-3 space-y-3 text-sm leading-relaxed text-slate-400">{children}</div>
  </section>
);

export default function PrivacyPolicy() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <Link
        to="/"
        data-testid="link-privacy-back"
        className="mb-8 inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-400 transition-colors hover:text-emerald-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div className="mb-8 flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
          <ShieldCheck className="h-6 w-6" />
        </span>
        <div>
          <h1 className="font-display text-2xl font-extrabold tracking-tight sm:text-3xl">
            Política de Privacidade
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Versão {VERSION} · vigente desde {UPDATED_AT}
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-700 bg-slate-800/60 p-6 sm:p-8">
        <Section title="1. Quem somos">
          <p>
            A <strong className="text-slate-200">Oficina Fácil</strong> é a plataforma que você usa para
            agendar serviços automotivos e acompanhar o andamento do seu veículo. Nesta política, "nós"
            se refere à Oficina Fácil, que trata seus dados pessoais como{" "}
            <strong className="text-slate-200">controladora</strong>, conforme a Lei Geral de Proteção de
            Dados (Lei nº 13.709/2018, "LGPD").
          </p>
          <p>
            Este projeto é uma demonstração acadêmica (Projeto Integrador). Mesmo assim, descrevemos aqui
            exatamente como os dados informados no sistema são tratados, para que o texto permaneça
            verdadeiro caso dados reais sejam usados.
          </p>
        </Section>

        <Section title="2. Quais dados coletamos">
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              <strong className="text-slate-200">Identificação e contato:</strong> nome completo e número
              de celular, informados no cadastro.
            </li>
            <li>
              <strong className="text-slate-200">Credenciais de acesso:</strong> uma senha, armazenada com
              hash pelo provedor de autenticação (Supabase Auth) — nunca em texto puro.
            </li>
            <li>
              <strong className="text-slate-200">Dados do veículo:</strong> marca, modelo e, opcionalmente,
              placa.
            </li>
            <li>
              <strong className="text-slate-200">Dados do agendamento:</strong> serviços escolhidos, datas,
              horários e o histórico de status do reparo (etapas de rastreio).
            </li>
            <li>
              <strong className="text-slate-200">Dados técnicos de segurança:</strong> endereço IP e
              horário das requisições, usados apenas para limitar tentativas abusivas de login e envio de
              código (rate limiting), sem associação a perfis de navegação.
            </li>
          </ul>
          <p>Não coletamos CPF, dados de pagamento ou dados sensíveis (art. 5º, II).</p>
        </Section>

        <Section title="3. Para que usamos seus dados e em qual base legal">
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              <strong className="text-slate-200">Criar e autenticar sua conta</strong> (cadastro e código de
              verificação por SMS): execução de contrato e, no envio do código, seu consentimento ao
              informar o celular (art. 7º, V e I).
            </li>
            <li>
              <strong className="text-slate-200">Agendar e prestar o serviço</strong> escolhido, inclusive
              atribuir um mecânico: execução de contrato (art. 7º, V).
            </li>
            <li>
              <strong className="text-slate-200">Notificar você</strong> sobre mudanças no status do seu
              veículo: execução de contrato.
            </li>
            <li>
              <strong className="text-slate-200">Proteger a plataforma</strong> (limite de tentativas,
              bloqueio de abuso): cumprimento de obrigação legal e legítimo interesse em segurança da
              informação (art. 7º, II e IX; arts. 46–48).
            </li>
          </ul>
        </Section>

        <Section title="4. Com quem compartilhamos">
          <p>
            Não vendemos nem alugamos seus dados. Compartilhamos o estritamente necessário com prestadores
            que operam a infraestrutura em nosso nome (operadores, art. 39):
          </p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              <strong className="text-slate-200">Supabase</strong> — hospedagem do banco de dados,
              autenticação e envio do código de verificação por SMS. A Supabase pode armazenar dados em
              servidores fora do Brasil, o que caracteriza transferência internacional (art. 33) amparada
              pelas cláusulas contratuais do provedor.
            </li>
          </ul>
          <p>Podemos divulgar dados caso a lei exija ou para proteger direitos da Oficina Fácil ou de terceiros.</p>
        </Section>

        <Section title="5. Onde seus dados ficam guardados no seu navegador">
          <p>
            Depois do login, guardamos seu token de sessão e seu nome no{" "}
            <strong className="text-slate-200">localStorage</strong> do seu navegador, só para manter você
            conectado entre acessos. Não usamos cookies de rastreamento ou de terceiros (publicidade,
            analytics). Esse dado some ao limpar os dados do site ou ao sair da conta.
          </p>
        </Section>

        <Section title="6. Por quanto tempo guardamos seus dados">
          <p>
            Mantemos seus dados cadastrais e o histórico de agendamentos enquanto sua conta estiver ativa.
            Se você pedir a exclusão da conta, apagamos os dados que não precisamos manter por obrigação
            legal (por exemplo, registros fiscais de serviços já prestados, quando aplicável).
          </p>
        </Section>

        <Section title="7. Seus direitos (art. 18 da LGPD)">
          <p>Você pode solicitar, a qualquer momento:</p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>confirmação de que tratamos seus dados e acesso a eles;</li>
            <li>correção de dados incompletos, inexatos ou desatualizados;</li>
            <li>exclusão ou anonimização de dados tratados com base no seu consentimento;</li>
            <li>portabilidade dos seus dados a outro fornecedor;</li>
            <li>revogação do consentimento dado.</li>
          </ul>
          <p>
            Para exercer qualquer um desses direitos, entre em contato pelo e-mail abaixo. Responderemos em
            prazo razoável.
          </p>
        </Section>

        <Section title="8. Segurança">
          <p>
            Usamos conexão criptografada (HTTPS), senhas protegidas por hash, controle de acesso por token
            para as áreas administrativas e limite de tentativas em ações sensíveis (login e envio de
            código). Nenhum sistema é 100% livre de risco; se identificarmos um incidente de segurança que
            afete seus dados, avisaremos você e a Autoridade Nacional de Proteção de Dados (ANPD) conforme
            exigido em lei.
          </p>
        </Section>

        <Section title="9. Alterações desta política">
          <p>
            Podemos atualizar esta política para refletir mudanças no serviço. Alterações relevantes serão
            publicadas aqui com uma nova versão e data. O uso continuado da plataforma após uma atualização
            significa que você está de acordo com o novo texto.
          </p>
        </Section>

        <Section title="10. Contato">
          <p>
            Dúvidas sobre esta política ou sobre o tratamento dos seus dados podem ser enviadas para{" "}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="font-semibold text-emerald-400 transition-colors hover:text-emerald-300"
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </Section>
      </div>
    </main>
  );
}
