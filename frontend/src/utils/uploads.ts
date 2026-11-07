import serverData from "./server-data";

export const uploadsAvailable = (flag = serverData.uploadsUnavailable) =>
  flag !== "true";
