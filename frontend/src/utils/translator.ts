import { useForm, type UseFormInput } from "@mantine/form";
import { zod4Resolver } from "mantine-form-zod-resolver";
import { useTranslation } from "react-i18next";
import { z } from "zod";

export function useTranslatedForm<T extends z.ZodType>(
  schema: T,
  options: UseFormInput<z.infer<T>>,
) {
  const { t } = useTranslation();

  return useForm<z.infer<T>>({
    ...options,
    validate: (values) => {
      const errors = zod4Resolver(schema)(values);

      return Object.fromEntries(
        Object.entries(errors).map(([key, value]) => [
          key,
          typeof value === "string" ? t(value) : value,
        ]),
      );
    },
  });
}
