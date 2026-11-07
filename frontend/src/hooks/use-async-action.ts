import { useRef, useState } from "react";

export function useAsyncAction<Args extends unknown[], Result>(
  action: (...args: Args) => Promise<Result>,
  onError?: (error: unknown) => void,
) {
  const runningRef = useRef(false);
  const [isRunning, setIsRunning] = useState(false);

  const run = async (...args: Args): Promise<Result | undefined> => {
    if (runningRef.current) return undefined;
    runningRef.current = true;
    setIsRunning(true);
    try {
      return await action(...args);
    } catch (error) {
      onError?.(error);
      return undefined;
    } finally {
      runningRef.current = false;
      setIsRunning(false);
    }
  };

  return { run, isRunning };
}
