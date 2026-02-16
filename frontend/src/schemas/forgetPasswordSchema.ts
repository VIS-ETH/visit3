import { z } from "zod";

export const forgetPasswordSchema = z
  .object({
    email: z.string(),
  })
  .refine((data) => z.email().safeParse(data.email).success, {
    message: "email.valid",
    path: ["email"],
  });
