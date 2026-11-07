import { z } from "zod";
import { zEmail } from "./utils";

export const loginSchema = z.object({
  username: zEmail("email.valid"),
  password: z.string().min(8, "password.min"),
});
