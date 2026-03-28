import en from "@/i18n/messages/en.json";
import zh from "@/i18n/messages/zh.json";
import ja from "@/i18n/messages/ja.json";

type Messages = typeof en;

const messagesMap: Record<string, Messages> = { en, zh, ja };

export function getTranslations(locale: string, namespace: string) {
  const messages = (messagesMap[locale] || en) as unknown as Record<string, any>;
  const fallback = en as unknown as Record<string, any>;

  return (key: string): string => {
    // Prefer nested namespace lookup: messages[namespace][key]
    const nested = messages[namespace]?.[key];
    if (nested) return nested;

    // Support flattened dotted keys like "layers.tools.label"
    const dotted = messages[`${namespace}.${key}`];
    if (dotted) return dotted;

    // Fallback to english messages with same strategy
    const nestedFallback = fallback[namespace]?.[key];
    if (nestedFallback) return nestedFallback;
    const dottedFallback = fallback[`${namespace}.${key}`];
    if (dottedFallback) return dottedFallback;

    return key;
  };
}
