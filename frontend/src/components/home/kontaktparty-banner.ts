import banner800 from "../../assets/home/kontaktparty-banner-800.webp";
import banner1200 from "../../assets/home/kontaktparty-banner-1200.webp";
import banner2000 from "../../assets/home/kontaktparty-banner-2000.webp";
import type { FeatureImage } from "../LinkFeatureCard";

export const KONTAKTPARTY_BANNER: FeatureImage = {
  src: banner1200,
  srcSet: `${banner800} 800w, ${banner1200} 1200w, ${banner2000} 2000w`,
  width: 2000,
  height: 626,
};
