import type {
  CompanyListResult,
  IndustryResponse,
  StaffUserResponse,
} from "../../orval/generated/fastAPI.schemas";
import { adminUser, staffUser } from "./users";

export { adminUser, staffUser };

export const memberUser: StaffUserResponse = {
  id: "33333333-3333-3333-3333-333333333333",
  email: "member@example.test",
  first_name: "Mem",
  last_name: "Ber",
  phone_number: "+41441111111",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  email_confirmed: false,
  company_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  company: { id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", name: "Acme AG" },
  created_at: "2026-03-14T09:30:00Z",
  last_login_at: null,
};

export const orphanUser: StaffUserResponse = {
  id: "44444444-4444-4444-4444-444444444444",
  email: "orphan@example.test",
  first_name: "Ora",
  last_name: "Phan",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  email_confirmed: true,
  created_at: "2025-11-02T08:00:00Z",
  last_login_at: "2026-09-28T16:45:00Z",
};

export const acmeCompany: CompanyListResult = {
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  name: "Acme AG",
  confirmed_at: "2026-01-01T00:00:00Z",
  users_count: 2,
  bookings_count: 1,
};

export const globexCompany: CompanyListResult = {
  id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  name: "Globex SA",
  confirmed_at: "2026-01-01T00:00:00Z",
  users_count: 0,
  bookings_count: 0,
};

export const softwareIndustry: IndustryResponse = {
  id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  name: "Software",
};
