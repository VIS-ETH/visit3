const HTTP_URL_PATTERN = /^https?:\/\//i;

export function isOptionalHttpUrl(value: string) {
  if (value === "") return true;
  return HTTP_URL_PATTERN.test(value) && URL.canParse(value);
}
