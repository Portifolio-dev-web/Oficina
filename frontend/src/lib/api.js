import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const authHeaders = (token) => ({ headers: { Authorization: `Bearer ${token}` } });

export const registerSendCode = (email) =>
  axios.post(`${API}/auth/register/send-code`, { email }).then((r) => r.data);

export const registerVerifyCode = (payload) =>
  axios.post(`${API}/auth/register/verify-code`, payload).then((r) => r.data);

export const login = (payload) =>
  axios.post(`${API}/auth/login`, payload).then((r) => r.data);

export const getMakes = () =>
  axios.get(`${API}/vehicles/makes`).then((r) => r.data);

export const getModels = (make) =>
  axios.get(`${API}/vehicles/models`, { params: { make } }).then((r) => r.data);

export const createAppointment = (payload, token) =>
  axios.post(`${API}/appointments`, payload, authHeaders(token)).then((r) => r.data);

export const getTracking = (id) =>
  axios.get(`${API}/tracking/${id}`).then((r) => r.data);

// Restrita ao admin (ver backend S1): exige o token do painel.
export const updateStage = (id, stage, token) =>
  axios
    .post(`${API}/tracking/${id}/status`, stage === undefined ? {} : { stage }, authHeaders(token))
    .then((r) => r.data);

export const adminLogin = (payload) =>
  axios.post(`${API}/admin/login`, payload).then((r) => r.data);

export const adminLogout = (token) =>
  axios.post(`${API}/admin/logout`, {}, authHeaders(token)).then((r) => r.data);

export const getAdminOverview = (token) =>
  axios.get(`${API}/admin/overview`, authHeaders(token)).then((r) => r.data);

export const toggleMechanic = (id, token) =>
  axios.post(`${API}/admin/mechanics/${id}/toggle`, {}, authHeaders(token)).then((r) => r.data);

export const createMechanic = (payload, token) =>
  axios.post(`${API}/admin/mechanics`, payload, authHeaders(token)).then((r) => r.data);

export const deleteMechanic = (id, token) =>
  axios.delete(`${API}/admin/mechanics/${id}`, authHeaders(token)).then((r) => r.data);
