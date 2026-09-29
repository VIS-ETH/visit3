import serverData from "./server-data";

export const uploadsAvailable = (flag: string | undefined) => flag !== "true";

export const UPLOADS_AVAILABLE = uploadsAvailable(
  serverData.uploadsUnavailable,
);
