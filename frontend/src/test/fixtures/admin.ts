import type {
  CompanyListResult,
  IndustryResponse,
  UserResponse,
} from "../../orval/generated/fastAPI.schemas";

export const adminUser: UserResponse = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "admin@example.test",
  first_name: "Ada",
  last_name: "Admin",
  is_staff: true,
  is_admin: true,
  is_company: false,
  is_kp_president: false,
  user_confirmed: true,
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

export const memberUser: UserResponse = {
  id: "33333333-3333-3333-3333-333333333333",
  email: "member@example.test",
  first_name: "Mem",
  last_name: "Ber",
  phone_number: "+41441111111",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  user_confirmed: false,
  email_confirmed: false,
  company_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  company: { id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", name: "Acme AG" },
};

export const orphanUser: UserResponse = {
  id: "44444444-4444-4444-4444-444444444444",
  email: "orphan@example.test",
  first_name: "Ora",
  last_name: "Phan",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  user_confirmed: true,
  email_confirmed: true,
};

export const acmeCompany: CompanyListResult = {
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  name: "Acme AG",
  users_count: 2,
  bookings_count: 1,
};

export const globexCompany: CompanyListResult = {
  id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  name: "Globex SA",
  users_count: 0,
  bookings_count: 0,
};

export const softwareIndustry: IndustryResponse = {
  id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  name: "Software",
};
