const encodeSegment = (value: object) =>
  btoa(JSON.stringify(value))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

export const createToken = (secondsUntilExpiry: number, subject = "user-1") =>
  [
    encodeSegment({ alg: "HS256", typ: "JWT" }),
    encodeSegment({
      sub: subject,
      roles: [],
      exp: Math.floor(Date.now() / 1000) + secondsUntilExpiry,
    }),
    "signature",
  ].join(".");
