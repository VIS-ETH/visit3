import { screen } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { SLOW_WAIT } from "../timeouts";

export const continueToBoothStep = async (user: UserEvent) => {
  await user.click(
    screen.getByRole("button", { name: "kp.booking.continue_to_booth" }),
  );
  await screen.findByText("kp.booking.booth_title", undefined, SLOW_WAIT);
};

export const continueToSummaryStep = async (user: UserEvent) => {
  await continueToBoothStep(user);
  await user.click(
    screen.getByRole("button", { name: "kp.booking.continue_to_summary" }),
  );
  await screen.findByText("kp.booking.summary_title", undefined, SLOW_WAIT);
};
