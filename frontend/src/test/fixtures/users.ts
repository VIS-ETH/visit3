import type { UserResponse } from "../../orval/generated/fastAPI.schemas";

export const adminUser: UserResponse = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "admin@example.test",
  first_name: "Ada",
  last_name: "Admin",
  is_staff: true,
  is_admin: true,
  is_company: false,
  is_kp_president: false,
  email_confirmed: true,
};

export const staffUser: UserResponse = {
  ...adminUser,
  id: "22222222-2222-2222-2222-222222222222",
  email: "staff@example.test",
  first_name: "Stan",
  last_name: "Staff",
  is_admin: false,
};

export const presidentUser: UserResponse = {
  ...staffUser,
  id: "44444444-4444-4444-4444-444444444444",
  email: "president@example.test",
  first_name: "Pia",
  last_name: "President",
  is_kp_president: true,
};

export const companyUser: UserResponse = {
  id: "55555555-5555-5555-5555-555555555555",
  email: "company@example.test",
  first_name: "Cora",
  last_name: "Company",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  email_confirmed: true,
};
