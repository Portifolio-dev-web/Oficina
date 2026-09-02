import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Car, ShieldCheck, MessageSquareText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { sendOtp, verifyOtp, getMakes, getModels } from "@/lib/api";

const maskPhone = (v) => {
  const d = v.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d.length ? `(${d}` : "";
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
};

const inputCls =
  "w-full rounded-xl border border-slate-700 bg-slate-800/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20";

export default function OnboardingModal({ open, onClose, onSuccess }) {
  const [step, setStep] = useState("form");
  const [form, setForm] = useState({ name: "", phone: "", password: "", make: "", model: "", plate: "" });
  const [makes, setMakes] = useState([]);
  const [models, setModels] = useState([]);
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [countdown, setCountdown] = useState(60);
  const [loading, setLoading] = useState(false);
  const refs = useRef([]);

  useEffect(() => {
    if (open) getMakes().then((d) => setMakes(d.makes)).catch(() => {});
  }, [open]);

  useEffect(() => {
    if (step === "otp" && countdown > 0) {
      const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [step, countdown]);

  useEffect(() => {
    if (!open) {
      setStep("form");
      setOtp(["", "", "", "", "", ""]);
      setCountdown(60);
    }
  }, [open]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleMakeChange = async (e) => {
    const make = e.target.value;
    setForm((f) => ({ ...f, make, model: "" }));
    setModels([]);
    if (make) {
      const d = await getModels(make);
      setModels(d.models);
    }
  };

  const formValid =
    form.name.trim().length >= 3 &&
    form.phone.replace(/\D/g, "").length >= 10 &&
    form.password.length >= 4 &&
    form.make &&
    form.model;

  const handleSendOtp = async () => {
    setLoading(true);
    try {
      const res = await sendOtp(form.phone);
      toast.success(res.message);
      toast(`[Simulação SMS] Seu código é: ${res.testCode}`, {
        icon: <MessageSquareText className="h-4 w-4" />,
        duration: 10000,
      });
      setStep("otp");
      setCountdown(60);
      setTimeout(() => refs.current[0]?.focus(), 250);
    } catch {
      toast.error("Não foi possível enviar o código. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (code) => {
    setLoading(true);
    try {
      const res = await verifyOtp({
        phone: form.phone,
        code,
        name: form.name,
        password: form.password,
        vehicle: { make: form.make, model: form.model, plate: form.plate.toUpperCase() },
      });
      toast.success("Cadastro verificado com sucesso!");
      onSuccess({ token: res.token, user: res.user });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Código inválido. Tente novamente.");
      setOtp(["", "", "", "", "", ""]);
      refs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = (i) => (e) => {
    const v = e.target.value.replace(/\D/g, "");
    if (!v) return;
    const next = [...otp];
    next[i] = v.slice(-1);
    setOtp(next);
    if (i < 5) refs.current[i + 1]?.focus();
    if (next.every(Boolean)) handleVerify(next.join(""));
  };

  const handleOtpKeyDown = (i) => (e) => {
    if (e.key === "Backspace") {
      e.preventDefault();
      const next = [...otp];
      if (next[i]) {
        next[i] = "";
        setOtp(next);
      } else if (i > 0) {
        next[i - 1] = "";
        setOtp(next);
        refs.current[i - 1]?.focus();
      }
    }
  };

  const handleOtpPaste = (e) => {
    e.preventDefault();
    const digits = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6).split("");
    if (!digits.length) return;
    const next = ["", "", "", "", "", ""];
    digits.forEach((d, i) => (next[i] = d));
    setOtp(next);
    if (next.every(Boolean)) handleVerify(next.join(""));
    else refs.current[digits.length]?.focus();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          data-testid="onboarding-modal"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            initial={{ opacity: 0, y: 32, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.97 }}
            transition={{ type: "spring", damping: 26, stiffness: 300 }}
            className="relative max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-2xl shadow-slate-950/60 sm:p-8"
          >
            <button
              data-testid="btn-close-onboarding"
              onClick={onClose}
              className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-700 hover:text-slate-200"
            >
              <X className="h-4 w-4" />
            </button>

            <AnimatePresence mode="wait">
              {step === "form" ? (
                <motion.div
                  key="form"
                  initial={{ opacity: 0, x: -24 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -24 }}
                  transition={{ duration: 0.22 }}
                >
                  <div className="mb-6 flex items-center gap-3">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
                      <Car className="h-6 w-6" />
                    </span>
                    <div>
                      <h2 className="font-display text-xl font-bold">Crie sua conta</h2>
                      <p className="text-xs text-slate-400">Cadastre-se e agende em menos de 1 minuto</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-slate-400">Nome completo</label>
                      <input
                        data-testid="input-name"
                        className={inputCls}
                        placeholder="Maria Silva"
                        value={form.name}
                        onChange={set("name")}
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-slate-400">Celular</label>
                      <input
                        data-testid="input-phone-number"
                        className={inputCls}
                        placeholder="(11) 99999-9999"
                        inputMode="numeric"
                        value={form.phone}
                        onChange={(e) => setForm((f) => ({ ...f, phone: maskPhone(e.target.value) }))}
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-slate-400">Senha</label>
                      <input
                        data-testid="input-password"
                        type="password"
                        className={inputCls}
                        placeholder="Mínimo 4 caracteres"
                        value={form.password}
                        onChange={set("password")}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-slate-400">Marca</label>
                        <select
                          data-testid="select-vehicle-brand"
                          className={inputCls}
                          value={form.make}
                          onChange={handleMakeChange}
                        >
                          <option value="">Selecione</option>
                          {makes.map((m) => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-slate-400">Modelo</label>
                        <select
                          data-testid="select-vehicle-model"
                          className={inputCls}
                          value={form.model}
                          onChange={set("model")}
                          disabled={!models.length}
                        >
                          <option value="">{form.make ? "Selecione" : "Escolha a marca"}</option>
                          {models.map((m) => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-slate-400">Placa (opcional)</label>
                      <input
                        data-testid="input-vehicle-plate"
                        className={`${inputCls} uppercase`}
                        placeholder="ABC1D23"
                        maxLength={8}
                        value={form.plate}
                        onChange={(e) => setForm((f) => ({ ...f, plate: e.target.value.toUpperCase() }))}
                      />
                    </div>
                    <button
                      data-testid="btn-send-otp"
                      disabled={!formValid || loading}
                      onClick={handleSendOtp}
                      className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 py-3.5 text-sm font-bold text-white transition-all hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                      Enviar código por SMS
                    </button>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="otp"
                  initial={{ opacity: 0, x: 24 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 24 }}
                  transition={{ duration: 0.22 }}
                >
                  <div className="mb-6 flex items-center gap-3">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/15 text-amber-400">
                      <ShieldCheck className="h-6 w-6" />
                    </span>
                    <div>
                      <h2 className="font-display text-xl font-bold">Verifique seu celular</h2>
                      <p className="text-xs text-slate-400">
                        Código enviado para <span className="font-semibold text-slate-300">{form.phone}</span>
                      </p>
                    </div>
                  </div>

                  <div className="mb-5 flex justify-between gap-2" onPaste={handleOtpPaste}>
                    {otp.map((d, i) => (
                      <input
                        key={i}
                        data-testid={`input-otp-digit-${i}`}
                        ref={(el) => (refs.current[i] = el)}
                        value={d}
                        onChange={handleOtpChange(i)}
                        onKeyDown={handleOtpKeyDown(i)}
                        inputMode="numeric"
                        maxLength={1}
                        className="h-14 w-11 rounded-xl border border-slate-700 bg-slate-900/70 text-center font-mono2 text-xl font-semibold text-emerald-300 outline-none transition-all focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/25 sm:w-12"
                      />
                    ))}
                  </div>

                  <button
                    data-testid="btn-verify-otp"
                    disabled={!otp.every(Boolean) || loading}
                    onClick={() => handleVerify(otp.join(""))}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 py-3.5 text-sm font-bold text-white transition-all hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                    Verificar e concluir cadastro
                  </button>

                  <div className="mt-4 text-center text-xs text-slate-400">
                    {countdown > 0 ? (
                      <span data-testid="otp-countdown">
                        Reenviar código em <span className="font-mono2 font-semibold text-amber-400">{countdown}s</span>
                      </span>
                    ) : (
                      <button
                        data-testid="btn-resend-otp"
                        onClick={handleSendOtp}
                        className="font-semibold text-emerald-400 transition-colors hover:text-emerald-300"
                      >
                        Reenviar código
                      </button>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
