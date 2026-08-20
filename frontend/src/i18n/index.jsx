import React, { createContext, useContext, useMemo, useState } from "react";
import { LANGS, MESSAGES } from "./messages";

const LANG_KEY = "avtoparty_lang";
const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    const saved = localStorage.getItem(LANG_KEY);
    return LANGS.includes(saved) ? saved : "ru";
  });

  const value = useMemo(() => {
    function t(key, vars) {
      const table = MESSAGES[lang] || MESSAGES.ru;
      let text = table[key] || MESSAGES.ru[key] || key;
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          text = text.replaceAll(`{${k}}`, String(v));
        });
      }
      return text;
    }
    function setLang(next) {
      setLangState(next);
      localStorage.setItem(LANG_KEY, next);
      document.documentElement.lang = next === "ky" ? "ky" : next;
    }
    return { lang, setLang, t };
  }, [lang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("I18nProvider missing");
  return ctx;
}
