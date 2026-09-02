import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const sendOtp = (phone) =>
  axios.post(`${API}/auth/send-otp`, { phone }).then((r) => r.data);

export const verifyOtp = (payload) =>
  axios.post(`${API}/auth/verify-otp`, payload).then((r) => r.data);

export const getMakes = () =>
  axios.get(`${API}/vehicles/makes`).then((r) => r.data);

export const getModels = (make) =>
  axios.get(`${API}/vehicles/models`, { params: { make } }).then((r) => r.data);

export const createAppointment = (payload) =>
  axios.post(`${API}/appointments`, payload).then((r) => r.data);

export const getTracking = (id) =>
  axios.get(`${API}/tracking/${id}`).then((r) => r.data);

export const updateStage = (id, stage) =>
  axios
    .post(`${API}/tracking/${id}/status`, stage === undefined ? {} : { stage })
    .then((r) => r.data);

const authHeaders = (token) => ({ headers: { Authorization: `Bearer ${token}` } });

export const adminLogin = (payload) =>
  axios.post(`${API}/admin/login`, payload).then((r) => r.data);

export const adminLogout = (token) =>
  axios.post(`${API}/admin/logout`, {}, authHeaders(token)).then((r) => r.data);

export const getAdminOverview = (token) =>
  axios.get(`${API}/admin/overview`, authHeaders(token)).then((r) => r.data);

export const toggleMechanic = (id, token) =>
  axios.post(`${API}/admin/mechanics/${id}/toggle`, {}, authHeaders(token)).then((r) => r.data);
