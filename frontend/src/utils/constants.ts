export interface ConfigOptions {
  primaryColor: string;
  logo: string;
  signet: string;
  base: string;
}

export function configOptions() {
  return (window as any).configOptions as ConfigOptions;
}
