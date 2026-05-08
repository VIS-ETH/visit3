// Source - https://stackoverflow.com/a/78046054
// Posted by Leo Aso
// Retrieved 2026-02-19, License - CC BY-SA 4.0

import parsePhoneNumberFromString from "libphonenumber-js";
import { z } from "zod";

export const zPhone = z.string().transform((arg, ctx) => {
  if (!arg) {
    return undefined;
  }
  const phone = parsePhoneNumberFromString(arg, {
    // set this to use a default country when the phone number omits country code
    defaultCountry: "CH",

    // set to false to require that the whole string is exactly a phone number,
    // otherwise, it will search for a phone number anywhere within the string
    extract: false,
  });

  // when it's good
  if (phone?.isValid()) {
    return phone.number;
  }

  // when it's not
  ctx.addIssue({
    code: "custom",
    message: "register.phoneNumber.invalid",
  });
  return z.NEVER;
});
