import { useSearchParams } from "react-router";

const PARAM = "changes";

export function useOnlyChangesParam(onChange?: () => void) {
  const [searchParams, setSearchParams] = useSearchParams();
  const onlyChanges = searchParams.get(PARAM) === "1";
  const setOnlyChanges = (value: boolean) => {
    onChange?.();
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) next.set(PARAM, "1");
        else next.delete(PARAM);
        return next;
      },
      { replace: true },
    );
  };
  return [onlyChanges, setOnlyChanges] as const;
}
