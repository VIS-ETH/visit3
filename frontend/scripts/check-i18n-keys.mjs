import fs from "node:fs";
import path from "node:path";

const rootDir = process.cwd();
const sourceDirs = [
  path.join(rootDir, "src", "pages"),
  path.join(rootDir, "src", "components"),
  path.join(rootDir, "src", "schemas")
];

const localePaths = {
  en: path.join(rootDir, "public", "locales", "en.json"),
  de: path.join(rootDir, "public", "locales", "de.json"),
};

const fileExtensions = new Set([".ts", ".tsx"]);

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(fullPath));
    } else if (fileExtensions.has(path.extname(entry.name))) {
      files.push(fullPath);
    }
  }

  return files;
}

function flattenKeys(value, prefix = "") {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return prefix ? [prefix] : [];
  }

  const keys = [];
  for (const [key, nestedValue] of Object.entries(value)) {
    const nextPrefix = prefix ? `${prefix}.${key}` : key;
    keys.push(...flattenKeys(nestedValue, nextPrefix));
  }

  return keys;
}

function collectTranslationUsages(source) {
  const keys = new Set();
  const patterns = [
    /\bt\(\s*["'`]([^"'`]+)["'`]\s*[\),]/g,
    /\bi18n\.t\(\s*["'`]([^"'`]+)["'`]\s*[\),]/g,
  ];

  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) {
      keys.add(match[1]);
    }
  }

  return keys;
}

function collectSchemaTranslationUsages(source) {
  const keys = new Set();
  const patterns = [
    /\bmessage:\s*["'`]([^"'`]+)["'`]/g,
    /\.(?:email|min|max|regex|refine)\([\s\S]*?["'`]([^"'`]+)["'`][\s\S]*?\)/g,
  ];

  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) {
      keys.add(match[1]);
    }
  }

  return keys;
}

function loadLocaleKeys(localePath) {
  const content = fs.readFileSync(localePath, "utf8");
  const parsed = JSON.parse(content);
  return new Set(flattenKeys(parsed));
}

const sourceFiles = sourceDirs.flatMap((dir) => (fs.existsSync(dir) ? walk(dir) : []));
const usedKeys = new Set();

for (const filePath of sourceFiles) {
  const source = fs.readFileSync(filePath, "utf8");
  for (const key of collectTranslationUsages(source)) {
    usedKeys.add(key);
  }
  if (filePath.includes(`${path.sep}src${path.sep}schemas${path.sep}`)) {
    for (const key of collectSchemaTranslationUsages(source)) {
      usedKeys.add(key);
    }
  }
}

const localeKeys = Object.fromEntries(
  Object.entries(localePaths).map(([locale, localePath]) => [
    locale,
    loadLocaleKeys(localePath),
  ]),
);

const missingByLocale = Object.fromEntries(
  Object.keys(localeKeys).map((locale) => [locale, []]),
);

for (const key of [...usedKeys].sort()) {
  for (const [locale, keys] of Object.entries(localeKeys)) {
    if (!keys.has(key)) {
      missingByLocale[locale].push(key);
    }
  }
}

const hasMissingKeys = Object.values(missingByLocale).some((keys) => keys.length > 0);

if (!hasMissingKeys) {
  console.log("i18n-keys: all referenced translation keys exist in en/de locale files.");
  process.exit(0);
}

console.error("i18n-keys: missing translation keys detected.");
for (const [locale, keys] of Object.entries(missingByLocale)) {
  if (keys.length === 0) continue;
  console.error(`\nMissing in ${locale}.json:`);
  for (const key of keys) {
    console.error(`- ${key}`);
  }
}

process.exit(1);
