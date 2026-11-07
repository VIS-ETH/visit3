import { notifications } from "@mantine/notifications";

export const notifySuccess = (message: string) =>
  notifications.show({ color: "green", message });

export const notifyError = (message: string) =>
  notifications.show({ color: "red", message });
