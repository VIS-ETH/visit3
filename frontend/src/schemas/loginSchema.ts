import { z } from "zod";

export const loginSchema = z
  .object({
    username: z.string(),
    password: z.string().min(11, "register.password.min"),
  })
  .refine((data) => z.email().safeParse(data.username).success, {
    message: "register.email.valid",
    path: ["username"],
  });