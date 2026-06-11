const DATA_IMAGE_PREFIX = "data:image/";

export function isOptionalImageSource(value: string) {
  if (value === "") return true;
  if (value.startsWith(DATA_IMAGE_PREFIX)) return true;
  return URL.canParse(value);
}
