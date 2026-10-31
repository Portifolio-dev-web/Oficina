import { useState } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { MotionConfig } from "framer-motion";
import { Toaster } from "sonner";
import Navbar from "@/components/Navbar";
import OnboardingModal from "@/components/OnboardingModal";
import Home from "@/pages/Home";
import Booking from "@/pages/Booking";
import Tracking from "@/pages/Tracking";
import Admin from "@/pages/Admin";
import PrivacyPolicy from "@/pages/PrivacyPolicy";
import { SessionContext, getSession, saveSession, clearSession } from "@/lib/session";

function Shell() {
  const [session, setSession] = useState(getSession);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const navigate = useNavigate();

  const openOnboarding = () => setOnboardingOpen(true);
  const signOut = () => {
    clearSession();
    setSession(null);
    navigate("/");
  };
  const handleSuccess = (s) => {
    saveSession(s);
    setSession(s);
    setOnboardingOpen(false);
    navigate("/agendar");
  };

  return (
    <SessionContext.Provider value={{ session, openOnboarding, signOut }}>
      <div className="min-h-screen bg-slate-900 text-slate-50">
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/agendar" element={<Booking />} />
          <Route path="/rastreio/:id" element={<Tracking />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/privacidade" element={<PrivacyPolicy />} />
        </Routes>
        <OnboardingModal
          open={onboardingOpen}
          onClose={() => setOnboardingOpen(false)}
          onSuccess={handleSuccess}
        />
      </div>
      <Toaster theme="dark" richColors position="top-center" duration={6000} />
    </SessionContext.Provider>
  );
}

export default function App() {
  return (
    // ACESSIBILIDADE (auditoria, item A5): com reducedMotion="user", o
    // Framer Motion desliga animações de transform/layout sozinho quando o
    // sistema do visitante tem "Reduzir movimento" ativado (WCAG 2.3.3),
    // sem precisar duplicar essa checagem em cada motion.div do app.
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </MotionConfig>
  );
}
