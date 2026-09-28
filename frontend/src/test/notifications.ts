import { vi } from "vitest";

export const notificationsShow = vi.fn();

export const resetNotificationsMock = () => {
  notificationsShow.mockReset();
};
