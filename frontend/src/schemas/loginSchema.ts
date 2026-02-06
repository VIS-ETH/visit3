import { z } from "zod";

export const loginSchema = z
  .object({
    username: z.string(),
    password: z.string().min(11, "password.min"),
  })
  .refine((data) => z.email().safeParse(data.username).success, {
    message: "email.valid",
    path: ["username"],
  });