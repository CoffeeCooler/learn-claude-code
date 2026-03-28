"use client";
import { createContext, useContext, ReactNode } from "react";
import en from "@/i18n/messages/en.json";
import zh from "@/i18n/messages/zh.json";
import ja from "@/i18n/messages/ja.json";

type Messages = typeof en;

const messagesMap: Record<string, Messages> = { en, zh, ja };

const I18nContext = createContext<{ locale: string; messages: Messages }>({
  locale: "en",
  messages: en,
});

export function I18nProvider({ locale, children }: { locale: string; children: ReactNode }) {
  const messages = messagesMap[locale] || en;
  return (
    <I18nContext.Provider value={{ locale, messages }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslations(namespace?: string) {
  const { messages } = useContext(I18nContext);
  return (key: string) => {
    const ns = namespace ? (messages as any)[namespace] : messages;
    if (!ns) return key;

    // Support nested dotted keys by walking the object
    if (typeof key === "string" && key.includes(".")) {
      const parts = key.split('.');
      let cur: any = ns;
      for (const p of parts) {
        if (cur == null) return key;
        cur = cur[p];
      }
      if (cur != null) return cur;
    }

    // 1) direct lookup on namespace object
    const direct = (ns as any)[key];
    if (direct) return direct;

    // 2) flattened dotted lookup: messages["namespace.key"]
    if (namespace) {
      const flat = (messages as any)[`${namespace}.${key}`];
      if (flat) return flat;
    }

    // 3) if no namespace, support dotted key lookup across root
    if (!namespace && typeof key === "string") {
      const dotted = (messages as any)[key];
      if (dotted) return dotted;
    }

    return key;
  };
}

export function useLocale() {
  return useContext(I18nContext).locale;
}
