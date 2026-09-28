import { z } from "zod";

const HTTP_URL_PATTERN = /^https?:\/\//i;
const emailSchema = z.email();

export function isOptionalHttpUrl(value: string) {
  if (value === "") return true;
  return HTTP_URL_PATTERN.test(value) && URL.canParse(value);
}

export function isOptionalEmail(value: string) {
  if (value === "") return true;
  return emailSchema.safeParse(value).success;
}
