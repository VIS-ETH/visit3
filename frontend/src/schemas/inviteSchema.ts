import { z } from "zod";
import { zEmail } from "./utils";

export const inviteSchema = z.object({
  email: zEmail("email.valid"),
});
