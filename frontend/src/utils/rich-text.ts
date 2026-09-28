const paragraphText = (node: Node): string => {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? "";
  if (node.nodeName === "BR") return "\n";
  return Array.from(node.childNodes).map(paragraphText).join("");
};

export const richTextPlain = (html: string) =>
  Array.from(new DOMParser().parseFromString(html, "text/html").body.children)
    .map(paragraphText)
    .filter((text) => text.trim().length > 0)
    .join("\n");

export const richTextLength = (html: string) => richTextPlain(html).length;
