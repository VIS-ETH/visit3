import {
  emptyKpFormValues,
  kpWithSettingsSchema,
} from "../../schemas/eventSettingsSchema";
import { useTranslatedForm } from "../../utils/translator";

export const useEventForm = (initialValues = emptyKpFormValues) =>
  useTranslatedForm<typeof kpWithSettingsSchema>(kpWithSettingsSchema, {
    initialValues,
  });
