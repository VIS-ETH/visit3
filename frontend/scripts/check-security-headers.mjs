const baseUrl = process.argv[2] ?? "http://localhost:3000";

const expectedHeaders = {
  "x-frame-options": (value) => value === "DENY",
  "x-content-type-options": (value) => value === "nosniff",
  "referrer-policy": (value) => value === "strict-origin-when-cross-origin",
  "permissions-policy": (value) => value.includes("camera=()"),
  "content-security-policy": (value) =>
    value.includes("frame-ancestors 'none'") &&
    value.includes("object-src 'none'") &&
    !value.includes("unsafe-eval") &&
    !value.includes("${"),
  server: (value) => !/\d/.test(value),
};

const paths = ["/", "/index.html", "/company/profile", "/missing-asset.js"];
const failures = [];

for (const path of paths) {
  const response = await fetch(new URL(path, baseUrl), { redirect: "manual" });
  for (const [name, isValid] of Object.entries(expectedHeaders)) {
    const value = response.headers.get(name);
    if (value === null || !isValid(value)) {
      failures.push(`${path}: ${name} = ${value}`);
    }
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log(`security headers ok on ${paths.length} paths of ${baseUrl}`);
