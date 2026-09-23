import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const rootDir = path.resolve(process.argv[2] ?? process.cwd());
const targetDir = path.join(rootDir, "src");

const fileExtensions = new Set([".tsx", ".ts"]);
const ignoredDirectoryNames = new Set(["generated"]);
const ignoredDirectories = new Set([
  path.join(rootDir, "src", "test", "fixtures"),
]);

const emptyOrWhitespaceOnly = /^\s*$/;
const placeholderStars = /^\*+$/;
const absoluteUrl = /^https?:\/\//i;
const routeLikePath = /^\/\w/;
const digitsOnly = /^\d+$/;
const envPlaceholder = /^%\w+%$/;
const singleLetterAmongPunctuation = /^[^A-Za-z]*[A-Za-z][^A-Za-z]*$/;
const translationKey = /^[a-z][a-z0-9_]*(\.[a-zA-Z0-9_$]+)+$/;

const ignoredTextPatterns = [
  emptyOrWhitespaceOnly,
  placeholderStars,
  absoluteUrl,
  routeLikePath,
  digitsOnly,
  envPlaceholder,
  singleLetterAmongPunctuation,
  translationKey,
];

const ignoredTextLiterals = new Set([
  "-",
  "@",
  ":",
  "|",
  "CHF",
  "VIS",
  "VISIT",
  "new Date(isoDate).getTime()",
]);

const userFacingJsxProps = new Set([
  "label",
  "title",
  "description",
  "placeholder",
  "aria-label",
  "alt",
  "error",
]);

const notificationPropNames = new Set(["message", "title"]);
const notificationCallNames = new Set([
  "notifications.show",
  "notifications.update",
]);
const schemaMessageMethods = new Set([
  "email",
  "min",
  "max",
  "regex",
  "refine",
]);

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (ignoredDirectoryNames.has(entry.name)) continue;
      if (ignoredDirectories.has(fullPath)) continue;
      files.push(...walk(fullPath));
    } else if (fileExtensions.has(path.extname(entry.name))) {
      files.push(fullPath);
    }
  }

  return files;
}

function shouldIgnoreLiteral(literal) {
  const text = literal.trim();
  if (!/[A-Za-z]/.test(text)) return true;
  if (ignoredTextLiterals.has(text)) return true;
  return ignoredTextPatterns.some((pattern) => pattern.test(text));
}

function collapseJsxText(text) {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

function plainStringLiteral(node) {
  if (node === undefined) return undefined;
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
    return node.text;
  }
  if (ts.isJsxExpression(node)) {
    return plainStringLiteral(node.expression);
  }
  return undefined;
}

function propertyKeyName(name) {
  if (ts.isIdentifier(name) || ts.isStringLiteral(name)) return name.text;
  return undefined;
}

function findViolations(filePath, source) {
  const isSchemaFile = filePath.includes(
    `${path.sep}src${path.sep}schemas${path.sep}`,
  );
  const sourceFile = ts.createSourceFile(
    filePath,
    source,
    ts.ScriptTarget.Latest,
    true,
    path.extname(filePath) === ".tsx" ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const violations = [];

  const addViolation = (position, literal) => {
    if (!literal || shouldIgnoreLiteral(literal)) return;
    const { line } = sourceFile.getLineAndCharacterOfPosition(position);
    violations.push({ line: line + 1, literal: literal.trim() });
  };

  const visitJsxText = (node) => {
    const literal = collapseJsxText(node.text);
    if (!literal) return;
    const leadingWhitespace = node.text.length - node.text.trimStart().length;
    addViolation(node.pos + leadingWhitespace, literal);
  };

  const visitJsxAttribute = (node) => {
    const name = node.name.getText(sourceFile);
    if (!userFacingJsxProps.has(name)) return;
    const literal = plainStringLiteral(node.initializer);
    if (literal === undefined) return;
    addViolation(node.getStart(sourceFile), literal);
  };

  const visitCall = (node) => {
    const calleeName = node.expression.getText(sourceFile);

    if (notificationCallNames.has(calleeName)) {
      const [argument] = node.arguments;
      if (argument !== undefined && ts.isObjectLiteralExpression(argument)) {
        for (const property of argument.properties) {
          if (!ts.isPropertyAssignment(property)) continue;
          const key = propertyKeyName(property.name);
          if (key === undefined || !notificationPropNames.has(key)) continue;
          addViolation(
            property.getStart(sourceFile),
            plainStringLiteral(property.initializer),
          );
        }
      }
    }

    if (!isSchemaFile) return;
    const methodName = ts.isPropertyAccessExpression(node.expression)
      ? node.expression.name.text
      : undefined;
    if (methodName === undefined || !schemaMessageMethods.has(methodName)) {
      return;
    }
    for (const argument of node.arguments) {
      addViolation(argument.getStart(sourceFile), plainStringLiteral(argument));
    }
  };

  const visit = (node) => {
    if (ts.isJsxText(node)) {
      visitJsxText(node);
    } else if (ts.isJsxAttribute(node)) {
      visitJsxAttribute(node);
    } else if (ts.isCallExpression(node)) {
      visitCall(node);
    } else if (
      isSchemaFile &&
      ts.isPropertyAssignment(node) &&
      propertyKeyName(node.name) === "message"
    ) {
      addViolation(
        node.getStart(sourceFile),
        plainStringLiteral(node.initializer),
      );
    }
    ts.forEachChild(node, visit);
  };

  visit(sourceFile);
  return violations;
}

const allFiles = fs.existsSync(targetDir) ? walk(targetDir) : [];
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
    console.error(
      `- ${relativeFile}:${violation.line} -> "${violation.literal}"`,
    );
  }
}

console.error(
  '\nUse t("...") keys for user-facing text or adjust the checker allowlist if needed.',
);
process.exit(1);
