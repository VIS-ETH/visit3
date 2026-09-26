import { KpEventServiceRequirementType } from "../orval/generated/fastAPI.schemas";

export const IMAGE_UPLOAD_ACCEPT = "image/png,image/jpeg,image/gif,image/webp";

export const LOGO_UPLOAD_ACCEPT = "image/png,image/jpeg,image/webp";

export const PDF_UPLOAD_ACCEPT = "application/pdf";

export const VIDEO_UPLOAD_ACCEPT = "video/mp4,video/quicktime,video/webm";

export const NAMETAG_BACKGROUND_ACCEPT = "image/png,image/jpeg";

export const LAYOUT_UPLOAD_ACCEPT = `${IMAGE_UPLOAD_ACCEPT},${PDF_UPLOAD_ACCEPT}`;

export const isAllowedImageType = (mimeType: string) =>
  IMAGE_UPLOAD_ACCEPT.split(",").includes(mimeType);

export const isAllowedLogoType = (mimeType: string) =>
  LOGO_UPLOAD_ACCEPT.split(",").includes(mimeType);

export const isAllowedLayoutType = (mimeType: string) =>
  LAYOUT_UPLOAD_ACCEPT.split(",").includes(mimeType);

export const isPdfSource = (source: string) => {
  const path = URL.canParse(source) ? new URL(source).pathname : source;
  return path.toLowerCase().endsWith(".pdf");
};

export const acceptForRequirement = (type: KpEventServiceRequirementType) => {
  if (type === KpEventServiceRequirementType.image) return IMAGE_UPLOAD_ACCEPT;
  if (type === KpEventServiceRequirementType.pdf) return PDF_UPLOAD_ACCEPT;
  if (type === KpEventServiceRequirementType.video) return VIDEO_UPLOAD_ACCEPT;
  return undefined;
};

export const allowedFormatsLabel = (
  type: KpEventServiceRequirementType,
  t: (key: string) => string,
) => {
  if (type === KpEventServiceRequirementType.image) {
    return t("kp.booking_manage.allowed_formats_image");
  }
  if (type === KpEventServiceRequirementType.pdf) {
    return t("kp.booking_manage.allowed_formats_pdf");
  }
  if (type === KpEventServiceRequirementType.video) {
    return t("kp.booking_manage.allowed_formats_video");
  }
  return t("kp.booking_manage.allowed_formats_file");
};
