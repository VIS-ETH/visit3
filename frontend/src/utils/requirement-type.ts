import { KpEventServiceRequirementType } from "../orval/generated/fastAPI.schemas";

type Translate = (key: string) => string;

const TYPE_LABEL_KEYS: Record<KpEventServiceRequirementType, string> = {
  [KpEventServiceRequirementType.text]: "kp.booking.requirement_type_text",
  [KpEventServiceRequirementType.file]: "kp.booking.requirement_type_file",
  [KpEventServiceRequirementType.image]: "kp.booking.requirement_type_image",
  [KpEventServiceRequirementType.pdf]: "kp.booking.requirement_type_pdf",
  [KpEventServiceRequirementType.video]: "kp.booking.requirement_type_video",
};

const UPLOAD_LABEL_KEYS: Record<KpEventServiceRequirementType, string> = {
  [KpEventServiceRequirementType.text]: "kp.booking.requirement_upload_file",
  [KpEventServiceRequirementType.file]: "kp.booking.requirement_upload_file",
  [KpEventServiceRequirementType.image]: "kp.booking.requirement_upload_image",
  [KpEventServiceRequirementType.pdf]: "kp.booking.requirement_upload_pdf",
  [KpEventServiceRequirementType.video]: "kp.booking.requirement_upload_video",
};

export const requirementTypeLabel = (
  type: KpEventServiceRequirementType,
  t: Translate,
) => t(TYPE_LABEL_KEYS[type]);

export const requirementUploadLabel = (
  type: KpEventServiceRequirementType,
  t: Translate,
) => t(UPLOAD_LABEL_KEYS[type]);
