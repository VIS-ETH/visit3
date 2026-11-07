export const PROFILE_DRAFT_PREFIX = "company-profile-draft";

export const removeProfileDraft = (key: string) => {
  try {
    localStorage.removeItem(key);
  } catch {
    return;
  }
};

export const clearProfileDrafts = () => {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(`${PROFILE_DRAFT_PREFIX}:`))
      .forEach(removeProfileDraft);
  } catch {
    return;
  }
};
