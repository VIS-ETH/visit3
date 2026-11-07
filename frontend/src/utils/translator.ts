import { useForm, type UseFormInput } from "@mantine/form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

const isBlank = (input: unknown) =>
  input === undefined || input === null || input === "";

const fallbackMessage = (issue: z.core.$ZodRawIssue) => {
  switch (issue.code) {
    case "invalid_type":
      if (isBlank(issue.input)) return "validation.required";
      if (issue.expected === "int") return "validation.invalid_integer";
      if (issue.expected === "number") return "validation.invalid_number";
      return "validation.invalid";
    case "too_small":
    case "too_big":
      return "validation.out_of_range";
    default:
      return "validation.invalid";
  }
};

const validationErrors = <T extends z.ZodType>(schema: T, values: unknown) => {
  const parsed = schema.safeParse(values, { error: fallbackMessage });
  if (parsed.success) return {};
  return Object.fromEntries(
    parsed.error.issues.map((issue) => [issue.path.join("."), issue.message]),
  );
};

export function useTranslatedForm<T extends z.ZodType<Record<string, unknown>>>(
  schema: T,
  options: UseFormInput<z.infer<T>>,
) {
  const { t } = useTranslation();

  return useForm<z.infer<T>>({
    validateInputOnChange: true,
    validateInputOnBlur: true,
    ...options,
    validate: (values) =>
      Object.fromEntries(
        Object.entries(validationErrors(schema, values)).map(
          ([key, message]) => [key, t(message)],
        ),
      ),
  });
}
