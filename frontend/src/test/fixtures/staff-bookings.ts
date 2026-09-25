import {
  KpBookingStatus,
  type BookingServiceResponse,
  type StaffBookingResponse,
  type StaffBoothZoneResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  testEventId,
  testFileRequirementId,
  testStaffBooking,
} from "./kp-booking";

const testMainHallZoneId = "99999999-9999-9999-9999-999999999991";
export const testSideHallZoneId = "99999999-9999-9999-9999-999999999992";

export const acmeBookingId = "aaaa0000-0000-0000-0000-000000000001";
export const betaBookingId = "aaaa0000-0000-0000-0000-000000000002";
export const zetaBookingId = "aaaa0000-0000-0000-0000-000000000003";

const zone = (
  id: string,
  name: string,
  capacity: number,
): StaffBoothZoneResponse => ({
  id,
  event_id: testEventId,
  name,
  description: name,
  color: "#112233",
  order: 1,
  capacity,
  booth_size: 6,
  base_price: 50000,
  layout_url: null,
  included_services: [],
});

export const testMainHallZone = zone(testMainHallZoneId, "Main hall", 10);
export const testSideHallZone = zone(testSideHallZoneId, "Side hall", 4);

const listedServices: BookingServiceResponse[] = (
  testStaffBooking.services ?? []
).map((bookingService) => ({
  ...bookingService,
  service: { ...bookingService.service, image_url: null },
}));

export const acmeBooking: StaffBookingResponse = {
  ...testStaffBooking,
  services: listedServices,
  id: acmeBookingId,
  booking_number: 1,
  booth_nr: 3,
  booth_zone: testMainHallZone,
  booth_zone_id: testMainHallZoneId,
  company: { id: "company-acme", name: "Acme AG" },
  company_id: "company-acme",
  is_complete: true,
  missing_items: [],
  status: KpBookingStatus.REGISTERED,
  status_changed_at: "2026-02-02T10:00:00Z",
};

const betaBooking: StaffBookingResponse = {
  ...testStaffBooking,
  services: listedServices,
  id: betaBookingId,
  booking_number: 2,
  booth_nr: null,
  booth_zone: testSideHallZone,
  booth_zone_id: testSideHallZoneId,
  company: { id: "company-beta", name: "Beta GmbH" },
  company_id: "company-beta",
  is_complete: false,
  missing_items: ["company_profile", `requirement:${testFileRequirementId}`],
  status: KpBookingStatus.REGISTERED,
  status_changed_at: "2026-02-01T09:00:00Z",
  waitlist_count: 2,
};

const zetaBooking: StaffBookingResponse = {
  ...testStaffBooking,
  services: listedServices,
  id: zetaBookingId,
  booking_number: 3,
  booth_nr: 7,
  booth_zone: testMainHallZone,
  booth_zone_id: testMainHallZoneId,
  company: { id: "company-zeta", name: "Zeta SA" },
  company_id: "company-zeta",
  confirmed_at: "2026-02-04T12:00:00Z",
  is_complete: true,
  missing_items: [],
  status: KpBookingStatus.CONFIRMED,
  status_changed_at: "2026-02-04T12:00:00Z",
};

export const staffBookings = [acmeBooking, betaBooking, zetaBooking];
