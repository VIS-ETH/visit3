import { useCallback, useEffect, useRef, useState } from "react";
import type { CompanyProfileResponse } from "../../orval/generated/fastAPI.schemas";
import {
  emptyCompanyProfileFormValues,
  toCompanyProfileFormValues,
  type CompanyProfileFormValues,
} from "../../schemas/companyProfileSchema";
import {
  PROFILE_DRAFT_PREFIX,
  removeProfileDraft,
} from "./profile-draft-storage";
const SAVE_DELAY_MS = 400;

type ProfileField = keyof CompanyProfileFormValues;
type PartialValues = Partial<Record<ProfileField, unknown>>;

interface StoredDraft {
  base: PartialValues;
  values: PartialValues;
}

type ProfileForm = {
  values: CompanyProfileFormValues;
  isDirty: () => boolean;
  getInitialValues: () => CompanyProfileFormValues;
  setValues: (values: Partial<CompanyProfileFormValues>) => void;
};

const isProfileField = (field: string): field is ProfileField =>
  field in emptyCompanyProfileFormValues;

const sameKind = (field: ProfileField, value: unknown) => {
  const empty = emptyCompanyProfileFormValues[field];
  return Array.isArray(empty)
    ? Array.isArray(value)
    : typeof empty === typeof value ||
        (empty === "" && typeof value === "number");
};

const sameValue = (left: unknown, right: unknown) =>
  JSON.stringify(left) === JSON.stringify(right);

const pickFields = (source: unknown): PartialValues => {
  if (typeof source !== "object" || source === null) return {};
  return Object.fromEntries(
    Object.entries(source).filter(
      ([field, value]) => isProfileField(field) && sameKind(field, value),
    ),
  );
};

const readDraft = (key: string): StoredDraft | null => {
  try {
    const stored = localStorage.getItem(key);
    if (!stored) return null;
    const parsed: unknown = JSON.parse(stored);
    if (typeof parsed !== "object" || parsed === null) return null;
    const { base, values } = parsed as { base?: unknown; values?: unknown };
    return { base: pickFields(base), values: pickFields(values) };
  } catch {
    return null;
  }
};

const writeDraft = (key: string, draft: StoredDraft) => {
  try {
    localStorage.setItem(key, JSON.stringify(draft));
  } catch {
    return;
  }
};

const changedFields = (
  values: CompanyProfileFormValues,
  base: CompanyProfileFormValues,
): StoredDraft => {
  const fields = (Object.keys(values) as ProfileField[]).filter(
    (field) => !sameValue(values[field], base[field]),
  );
  return {
    base: Object.fromEntries(fields.map((field) => [field, base[field]])),
    values: Object.fromEntries(fields.map((field) => [field, values[field]])),
  };
};

const applicableDraft = (
  draft: StoredDraft,
  saved: CompanyProfileFormValues,
): Partial<CompanyProfileFormValues> =>
  Object.fromEntries(
    (Object.keys(draft.values) as ProfileField[])
      .filter(
        (field) =>
          field in draft.base &&
          sameValue(draft.base[field], saved[field]) &&
          !sameValue(draft.values[field], saved[field]),
      )
      .map((field) => [field, draft.values[field]]),
  );

export const useProfileDraft = (
  form: ProfileForm,
  profile: CompanyProfileResponse | undefined,
  scope: string,
  applyValues: (values: CompanyProfileFormValues) => void,
) => {
  const [restored, setRestored] = useState(false);
  const loadedKeyRef = useRef<string | null>(null);
  const key = profile
    ? `${PROFILE_DRAFT_PREFIX}:${scope}:${profile.company_id}`
    : null;

  useEffect(() => {
    if (!profile || key === null || loadedKeyRef.current === key) return;
    loadedKeyRef.current = key;
    const saved = toCompanyProfileFormValues(profile);
    applyValues(saved);
    const draft = readDraft(key);
    if (draft === null) return;
    const changes = applicableDraft(draft, saved);
    if (Object.keys(changes).length === 0) {
      removeProfileDraft(key);
      return;
    }
    form.setValues(changes);
    setRestored(true);
  }, [profile, key, applyValues, form]);

  const isDirty = form.isDirty();
  const values = form.values;

  useEffect(() => {
    if (key === null || loadedKeyRef.current !== key) return;
    const timer = setTimeout(() => {
      if (isDirty)
        writeDraft(key, changedFields(values, form.getInitialValues()));
      else removeProfileDraft(key);
    }, SAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [key, isDirty, values, form]);

  const clearDraft = useCallback(() => {
    if (key !== null) removeProfileDraft(key);
    setRestored(false);
  }, [key]);

  return { restored, clearDraft };
};
