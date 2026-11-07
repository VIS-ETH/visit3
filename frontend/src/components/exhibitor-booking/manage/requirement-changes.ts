type RequirementChangeTarget = {
  bookingServiceId: string;
  requirementId: string;
  serviceName: string;
  requirementName: string;
};

export type PendingRequirementChange =
  | (RequirementChangeTarget & { kind: "text"; text: string })
  | (RequirementChangeTarget & { kind: "file"; file: File })
  | (RequirementChangeTarget & { kind: "delete_file" });

export type RequirementCompletion = Record<string, boolean>;

export const requirementChangeKey = (
  bookingServiceId: string,
  requirementId: string,
) => `${bookingServiceId}:${requirementId}`;

export const changeKey = (change: PendingRequirementChange) =>
  requirementChangeKey(change.bookingServiceId, change.requirementId);

export const requirementChangeLabel = (
  change: PendingRequirementChange,
  t: (key: string) => string,
) => {
  if (change.kind === "text") return t("kp.booking_manage.change_text");
  if (change.kind === "file") return t("kp.booking_manage.change_file");
  return t("kp.booking_manage.change_delete_file");
};
