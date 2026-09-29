import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import HttpBackend from "i18next-http-backend";
import { LOCALE_LOAD_PATH } from "./utils/locale-load-path";

const namespaces = ["common", "auth", "account", "admin", "kp"];

i18n
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "en",
    supportedLngs: ["en", "de"],
    ns: namespaces,
    defaultNS: "common",
    fallbackNS: namespaces.filter((namespace) => namespace !== "common"),
    debug: true,
    interpolation: {
      escapeValue: false,
    },
    backend: {
      loadPath: LOCALE_LOAD_PATH,
    },
  });

export default i18n;
