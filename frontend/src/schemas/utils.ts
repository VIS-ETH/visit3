// Source - https://stackoverflow.com/a/78046054
// Posted by Leo Aso
// Retrieved 2026-02-19, License - CC BY-SA 4.0

import parsePhoneNumberFromString from "libphonenumber-js";
import { z } from "zod";

const COUNTRY_ASSUMED_WHEN_THE_COUNTRY_CODE_IS_OMITTED = "CH";
const SEARCH_FOR_A_PHONE_NUMBER_INSIDE_SURROUNDING_TEXT = false;

export const zPhone = z.string().transform((arg, ctx) => {
  if (!arg) {
    return undefined;
  }
  const phone = parsePhoneNumberFromString(arg, {
    defaultCountry: COUNTRY_ASSUMED_WHEN_THE_COUNTRY_CODE_IS_OMITTED,
    extract: SEARCH_FOR_A_PHONE_NUMBER_INSIDE_SURROUNDING_TEXT,
  });

  if (phone?.isValid()) {
    return phone.number;
  }

  ctx.addIssue({
    code: "custom",
    message: "register.phoneNumber.invalid",
  });
  return z.NEVER;
});
