import banner800 from "../../assets/home/kontaktparty-banner-800.webp";
import banner1200 from "../../assets/home/kontaktparty-banner-1200.webp";
import banner2000 from "../../assets/home/kontaktparty-banner-2000.webp";
import type { EventBannerResponse } from "../../orval/generated/fastAPI.schemas";
import type { FeatureImage } from "../LinkFeatureCard";

const PREFERRED_SOURCE_WIDTH = 1200;

export const KONTAKTPARTY_BANNER: FeatureImage = {
  src: banner1200,
  srcSet: `${banner800} 800w, ${banner1200} 1200w, ${banner2000} 2000w`,
  width: 2000,
  height: 626,
};

export const eventBannerImage = (
  banner: EventBannerResponse | null | undefined,
): FeatureImage => {
  if (!banner?.sources.length) return KONTAKTPARTY_BANNER;
  const preferred =
    banner.sources.find((source) => source.width >= PREFERRED_SOURCE_WIDTH) ??
    banner.sources[banner.sources.length - 1];
  return {
    src: preferred.url,
    srcSet: banner.sources
      .map((source) => `${source.url} ${source.width}w`)
      .join(", "),
    width: banner.width,
    height: banner.height,
  };
};
