import { useCallback, useEffect, useRef, useState } from "react";
import type { CompanyProfileResponse } from "../../orval/generated/fastAPI.schemas";
import {
  emptyCompanyProfileFormValues,
  toCompanyProfileFormValues,
  type CompanyProfileFormValues,
} from "../../schemas/companyProfileSchema";

const DRAFT_PREFIX = "company-profile-draft";
const SAVE_DELAY_MS = 400;

type ProfileForm = {
  values: CompanyProfileFormValues;
  isDirty: () => boolean;
  setValues: (values: CompanyProfileFormValues) => void;
};

const sameKind = (left: unknown, right: unknown) =>
  Array.isArray(left)
    ? Array.isArray(right)
    : typeof left === typeof right ||
      (left === "" && typeof right === "number");

const readDraft = (key: string): Partial<CompanyProfileFormValues> | null => {
  try {
    const stored = localStorage.getItem(key);
    if (!stored) return null;
    const parsed: unknown = JSON.parse(stored);
    if (typeof parsed !== "object" || parsed === null) return null;
    return Object.fromEntries(
      Object.entries(parsed).filter(
        ([field, value]) =>
          field in emptyCompanyProfileFormValues &&
          sameKind(
            emptyCompanyProfileFormValues[
              field as keyof CompanyProfileFormValues
            ],
            value,
          ),
      ),
    );
  } catch {
    return null;
  }
};

const writeDraft = (key: string, values: CompanyProfileFormValues) => {
  try {
    localStorage.setItem(key, JSON.stringify(values));
  } catch {
    // Drafts are a convenience; a full or blocked storage must not break the form.
  }
};

const removeDraft = (key: string) => {
  try {
    localStorage.removeItem(key);
  } catch {
    // See writeDraft.
  }
};

export const useProfileDraft = (
  form: ProfileForm,
  profile: CompanyProfileResponse | undefined,
  scope: string,
  applyValues: (values: CompanyProfileFormValues) => void,
) => {
  const [restored, setRestored] = useState(false);
  const loadedKeyRef = useRef<string | null>(null);
  const key = profile ? `${DRAFT_PREFIX}:${scope}:${profile.company_id}` : null;

  useEffect(() => {
    if (!profile || key === null || loadedKeyRef.current === key) return;
    loadedKeyRef.current = key;
    const saved = toCompanyProfileFormValues(profile);
    applyValues(saved);
    const draft = readDraft(key);
    if (draft === null) return;
    const merged = { ...saved, ...draft };
    if (JSON.stringify(merged) === JSON.stringify(saved)) {
      removeDraft(key);
      return;
    }
    form.setValues(merged);
    setRestored(true);
  }, [profile, key, applyValues, form]);

  const isDirty = form.isDirty();
  const values = form.values;

  useEffect(() => {
    if (key === null || loadedKeyRef.current !== key) return;
    const timer = setTimeout(() => {
      if (isDirty) writeDraft(key, values);
      else removeDraft(key);
    }, SAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [key, isDirty, values]);

  const clearDraft = useCallback(() => {
    if (key !== null) removeDraft(key);
    setRestored(false);
  }, [key]);

  return { restored, clearDraft };
};
