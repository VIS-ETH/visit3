import { z } from "zod";

const registerSchema = z.object({
  email: z.string(),
  password: z.string().min(11, "register.password.min"),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "register.password.nomatch",
  path: ["confirmPassword"], 
});

export default registerSchema;