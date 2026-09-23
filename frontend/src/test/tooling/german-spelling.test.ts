import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

type GermanText = [string, string];

const frontendRoot = process.cwd();
const germanLocaleDir = path.join(frontendRoot, "public", "locales", "de");
const mailDefaultsFile = path.join(
  frontendRoot,
  "..",
  "backend",
  "app",
  "mail_templates",
  "defaults.py",
);

const LEGITIMATE_SPELLINGS = [
  "abenteuer",
  "aktuell",
  "betreu",
  "dauer",
  "erneuer",
  "feuer",
  "israel",
  "jubilaeum",
  "manuel",
  "michael",
  "neue",
  "queue",
  "scheuer",
  "steuer",
  "treue",
  "zuerst",
];

const TRANSLITERATION = /ae|oe|ue/;
const GERMAN_WORD = /[A-Za-zÄÖÜäöüß]+/g;
const STRING_LITERAL = /"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)'/g;
const GERMAN_FIELD = /\b(?:subject|body)_de=/g;
const TEMPLATE_KEY = /MailTemplateKey\.(\w+)/g;

const withoutMarkup = (text: string) =>
  text.replace(/<[^>]*>/g, " ").replace(/\{\{.*?\}\}/g, " ");

const wordsOf = (text: string) => withoutMarkup(text).match(GERMAN_WORD) ?? [];

const isTransliterated = (word: string) => {
  const lowercased = word.toLowerCase();
  if (!TRANSLITERATION.test(lowercased)) return false;
  return !LEGITIMATE_SPELLINGS.some((spelling) =>
    lowercased.includes(spelling),
  );
};

const flattenValues = (value: unknown, prefix = ""): GermanText[] => {
  if (typeof value === "string") return [[prefix, value]];
  if (typeof value !== "object" || value === null) return [];
  return Object.entries(value).flatMap(([key, nested]) =>
    flattenValues(nested, prefix ? `${prefix}.${key}` : key),
  );
};

const localeTexts = (): GermanText[] =>
  fs
    .readdirSync(germanLocaleDir)
    .filter((file) => file.endsWith(".json"))
    .flatMap((file) =>
      flattenValues(
        JSON.parse(fs.readFileSync(path.join(germanLocaleDir, file), "utf8")),
      ).map(([key, text]): GermanText => [`${file}:${key}`, text]),
    );

const templateKeyBefore = (source: string, index: number) => {
  const keys = [...source.slice(0, index).matchAll(TEMPLATE_KEY)];
  const lastKey = keys.at(-1);
  return lastKey ? lastKey[1] : "unknown";
};

const mailTemplateTexts = (): GermanText[] => {
  const source = fs.readFileSync(mailDefaultsFile, "utf8");
  return [...source.matchAll(GERMAN_FIELD)].flatMap((field) => {
    const start = field.index + field[0].length;
    const end = source.indexOf("_en=", start);
    const chunk = source.slice(start, end === -1 ? source.length : end);
    const key = `defaults.py:${templateKeyBefore(source, field.index)}`;
    return [...chunk.matchAll(STRING_LITERAL)].map((literal): GermanText => [
      key,
      literal.slice(1).find(Boolean) ?? "",
    ]);
  });
};

const germanTexts = [...localeTexts(), ...mailTemplateTexts()];

const offendersMatching = (predicate: (text: string) => boolean) =>
  germanTexts.filter(([, text]) => predicate(text)).map(([key]) => key);

describe("the transliteration rule", () => {
  it("flags words that spell an umlaut out", () => {
    expect(isTransliterated("Standgroesse")).toBe(true);
    expect(isTransliterated("Buehne")).toBe(true);
    expect(isTransliterated("Anhaenge")).toBe(true);
  });

  it("accepts words that legitimately contain the letter pairs", () => {
    expect(isTransliterated("aktuelles")).toBe(false);
    expect(isTransliterated("Steuernummer")).toBe(false);
    expect(isTransliterated("Neue")).toBe(false);
    expect(isTransliterated("Michael")).toBe(false);
    expect(isTransliterated("Standgrösse")).toBe(false);
  });
});

describe("the german texts", () => {
  it("covers the locale files and the mail template defaults", () => {
    expect(localeTexts().length).toBeGreaterThan(0);
    expect(mailTemplateTexts().length).toBeGreaterThan(0);
  });

  it("spell umlauts instead of transliterating them", () => {
    const offenders = germanTexts.flatMap(([key, text]) =>
      wordsOf(text)
        .filter(isTransliterated)
        .map((word) => `${key}: ${word}`),
    );

    expect(offenders).toEqual([]);
  });

  it("use the swiss double s", () => {
    expect(offendersMatching((text) => text.includes("ß"))).toEqual([]);
  });
});
