import { createContext, useContext } from "react";

const KEY = "autofix_session";

export const getSession = () => {
  try {
    return JSON.parse(localStorage.getItem(KEY));
  } catch {
    return null;
  }
};

export const saveSession = (s) => localStorage.setItem(KEY, JSON.stringify(s));
export const clearSession = () => localStorage.removeItem(KEY);

export const SessionContext = createContext(null);
export const useSession = () => useContext(SessionContext);
