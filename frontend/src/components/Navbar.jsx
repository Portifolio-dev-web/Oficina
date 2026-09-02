import { useNavigate, Link } from "react-router-dom";
import { Wrench, LogOut, CalendarPlus, LayoutDashboard } from "lucide-react";
import { useSession } from "@/lib/session";

export default function Navbar() {
  const { session, openOnboarding, signOut } = useSession();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-700/60 bg-slate-900/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" data-testid="nav-brand-logo" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500 shadow-[0_0_18px_rgba(16,185,129,0.4)]">
            <Wrench className="h-5 w-5 text-white" />
          </span>
          <span className="font-display text-lg font-bold tracking-tight">
            AutoFix <span className="text-emerald-400">Pro</span>
          </span>
        </Link>

        <div className="flex items-center gap-3">
          <Link
            to="/admin"
            data-testid="nav-admin-link"
            className="flex items-center gap-1.5 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 transition-colors hover:border-amber-500/60 hover:text-amber-300"
          >
            <LayoutDashboard className="h-3.5 w-3.5" />
            Painel Oficina
          </Link>
          {session ? (
            <>
              <span className="hidden text-sm text-slate-400 sm:block">
                Olá, <span className="font-semibold text-slate-200">{session.user.name.split(" ")[0]}</span>
              </span>
              <button
                data-testid="btn-nav-agendar"
                onClick={() => navigate("/agendar")}
                className="flex items-center gap-2 rounded-full bg-emerald-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-600"
              >
                <CalendarPlus className="h-4 w-4" />
                <span className="hidden sm:inline">Novo agendamento</span>
                <span className="sm:hidden">Agendar</span>
              </button>
              <button
                data-testid="btn-sign-out"
                onClick={signOut}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-700 text-slate-400 transition-colors hover:border-slate-500 hover:text-slate-200"
                title="Sair"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </>
          ) : (
            <button
              data-testid="btn-open-onboarding"
              onClick={openOnboarding}
              className="rounded-full bg-emerald-500 px-5 py-2 text-sm font-semibold text-white shadow-[0_0_18px_rgba(16,185,129,0.35)] transition-all hover:bg-emerald-600 hover:shadow-[0_0_24px_rgba(16,185,129,0.5)]"
            >
              Entrar / Cadastrar
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
