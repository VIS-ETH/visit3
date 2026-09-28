export const swapped = <T>(items: T[], index: number, target: number) => {
  const reordered = [...items];
  [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
  return reordered;
};
