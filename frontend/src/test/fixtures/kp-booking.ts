import {
  KpBookingStatus,
  KpEventServiceRequirementType,
  KpServiceCategory,
  type BookingResponse,
  type KpResponse,
  type MyBookingResponse,
  type ServiceRequirementResponse,
  type ServiceResponse,
  type StaffBookingResponse,
} from "../../orval/generated/fastAPI.schemas";

export const testEventId = "11111111-1111-1111-1111-111111111111";
export const testBookingId = "22222222-2222-2222-2222-222222222222";
export const testBookingServiceId = "33333333-3333-3333-3333-333333333333";
export const testFileRequirementId = "44444444-4444-4444-4444-444444444444";
export const testTextRequirementId = "55555555-5555-5555-5555-555555555555";
export const testServiceId = "66666666-6666-6666-6666-666666666666";

export const testEvent: KpResponse = {
  id: testEventId,
  name: "Kontaktparty",
  registration_open: "2026-01-01T00:00:00Z",
  registration_end: "2026-02-01T00:00:00Z",
  finalization_deadline: "2026-03-01T00:00:00Z",
  nametags_deadline: "2026-03-15T00:00:00Z",
  event_date: "2026-04-01T00:00:00Z",
  vat_rate_percent: 8.1,
  terms_url: null,
  finalization_reminder_days: 3,
  max_nametags_per_booking: 5,
};

const fileRequirement: ServiceRequirementResponse = {
  id: testFileRequirementId,
  service_id: testServiceId,
  type: KpEventServiceRequirementType.pdf,
  name: "Company brochure",
  description: "A brochure for the booth",
  order: 1,
};

const textRequirement: ServiceRequirementResponse = {
  id: testTextRequirementId,
  service_id: testServiceId,
  type: KpEventServiceRequirementType.text,
  name: "Company slogan",
  description: "A short slogan",
  order: 2,
};

const bookedService: ServiceResponse = {
  id: testServiceId,
  event_id: testEventId,
  name: "Booth package",
  description: "Everything for the booth",
  confirmation_description: null,
  order: 1,
  price: 10000,
  max_quantity_per_booking: 1,
  max_total_quantity: 10,
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  remaining_total_quantity: 4,
  is_active: true,
  requirements: [fileRequirement, textRequirement],
};

const boothZone = {
  id: "77777777-7777-7777-7777-777777777777",
  event_id: testEventId,
  name: "Main hall",
  description: "Main hall zone",
  color: "#112233",
  order: 1,
  capacity: 20,
  booth_size: 6,
  base_price: 50000,
  included_services: [],
};

export const testBooking: BookingResponse = {
  id: testBookingId,
  booking_number: 42,
  event_id: testEventId,
  company_id: "88888888-8888-8888-8888-888888888888",
  booth_zone_id: boothZone.id,
  booth_nr: 3,
  status: KpBookingStatus.REGISTERED,
  booth_zone: boothZone,
  services: [
    {
      id: testBookingServiceId,
      booking_id: testBookingId,
      service_id: testServiceId,
      quantity: 1,
      included_quantity: 0,
      charged_quantity: 1,
      unit_price: 10000,
      line_net: 10000,
      service: bookedService,
    },
  ],
  net_total: 60000,
  price: { net: 60000, vat: 4860, gross: 64860 },
};

export const testOpenEvent: KpResponse = {
  ...testEvent,
  registration_open: "2000-01-01",
  registration_end: "2099-12-31",
  finalization_deadline: "2099-12-31",
  nametags_deadline: "2099-12-31",
  event_date: "2099-12-31",
};

export const testRejectedBooking: MyBookingResponse = {
  ...testBooking,
  status: KpBookingStatus.REJECTED,
  rejection_reason: "Zone already assigned to another company",
  can_register: true,
};

export const testCancelledBooking: MyBookingResponse = {
  ...testBooking,
  status: KpBookingStatus.CANCELLED,
  can_register: false,
};

export const testStaffBooking: StaffBookingResponse = {
  id: testBookingId,
  booking_number: 42,
  event_id: testEventId,
  company_id: "88888888-8888-8888-8888-888888888888",
  booth_zone_id: boothZone.id,
  booth_nr: 3,
  status: KpBookingStatus.REGISTERED,
  company: { id: "88888888-8888-8888-8888-888888888888", name: "Acme AG" },
  booth_zone: boothZone,
  services: testBooking.services,
  net_total: 60000,
  price: { net: 60000, vat: 4860, gross: 64860 },
  booked_services_count: 1,
  booked_services_summary: "Booth package",
  nametag_count: 2,
  waitlist_count: 0,
  company_details_submitted: true,
};
