import { z } from "zod";
import { zEmail } from "./utils";

export const passwordResetRequestSchema = z.object({
  email: zEmail("email.valid"),
});
