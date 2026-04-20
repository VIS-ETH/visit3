import fs from "node:fs";
import path from "node:path";

const rootDir = process.cwd();
const targetDirs = [
  path.join(rootDir, "src", "pages"),
  path.join(rootDir, "src", "components"),
];

const fileExtensions = new Set([".tsx"]);

const ignoredTextPatterns = [
  /^\s*$/, // empty/whitespace
  /^\*+$/, // placeholder stars
  /^https?:\/\//i,
  /^\/\w/, // route-like string
  /^\d+$/, // numeric only
  /^%\w+%$/, // env placeholders
];

const ignoredTextLiterals = new Set([
  "-",
  "@",
  ":",
  "|",
]);

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

function shouldIgnoreLiteral(literal) {
  const text = literal.trim();
  if (ignoredTextLiterals.has(text)) return true;
  return ignoredTextPatterns.some((pattern) => pattern.test(text));
}

function findViolations(filePath, source) {
  const violations = [];
  const lines = source.split(/\r?\n/);

  lines.forEach((line, index) => {
    const lineNumber = index + 1;

    // Catch plain JSX text nodes: >Some text<
    const textNodeMatches = [...line.matchAll(/>([^<{]*[A-Za-z][^<{]*)</g)];
    for (const match of textNodeMatches) {
      const literal = (match[1] || "").trim();
      if (!literal || shouldIgnoreLiteral(literal)) continue;
      if (literal.includes("{")) continue;
      violations.push({ line: lineNumber, literal });
    }

    // Catch common user-facing string props in JSX
    const propMatches = [
      ...line.matchAll(/\b(label|title|description|placeholder)="([^"]*[A-Za-z][^"]*)"/g),
    ];

    for (const match of propMatches) {
      const literal = (match[2] || "").trim();
      if (!literal || shouldIgnoreLiteral(literal)) continue;
      violations.push({ line: lineNumber, literal });
    }
  });

  return violations;
}

const allFiles = targetDirs.flatMap((dir) => (fs.existsSync(dir) ? walk(dir) : []));
const report = [];

for (const filePath of allFiles) {
  const source = fs.readFileSync(filePath, "utf8");
  const violations = findViolations(filePath, source);
  if (violations.length > 0) {
    report.push({ filePath, violations });
  }
}

if (report.length === 0) {
  console.log("i18n-check: no obvious hardcoded user-facing literals found.");
  process.exit(0);
}

console.error("i18n-check: found potential hardcoded user-facing literals:");
for (const item of report) {
  const relativeFile = path.relative(rootDir, item.filePath);
  for (const violation of item.violations) {
    console.error(`- ${relativeFile}:${violation.line} -> \"${violation.literal}\"`);
  }
}

console.error("\nUse t(\"...\") keys for user-facing text or adjust the checker allowlist if needed.");
process.exit(1);
