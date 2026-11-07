import { useRef, useState } from "react";
import { downloadBlob } from "../utils/download";

export function useDownloads() {
  const runningRef = useRef(new Set<string>());
  const [running, setRunning] = useState<ReadonlySet<string>>(new Set());

  const update = () => setRunning(new Set(runningRef.current));

  const download = async (
    key: string,
    fetchContent: () => Promise<unknown>,
    filename: string,
  ) => {
    if (runningRef.current.has(key)) return;
    runningRef.current.add(key);
    update();
    try {
      downloadBlob(await fetchContent(), filename);
    } catch {
      return;
    } finally {
      runningRef.current.delete(key);
      update();
    }
  };

  return { download, isDownloading: (key: string) => running.has(key) };
}
