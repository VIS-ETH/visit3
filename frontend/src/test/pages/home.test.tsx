import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import Home from "../../pages/Home";
import { UserContext } from "../../context/useCurrentUser";
import { renderWithProviders } from "../render";
import banner800 from "../../assets/home/kontaktparty-banner-800.webp";
import banner1200 from "../../assets/home/kontaktparty-banner-1200.webp";
import banner2000 from "../../assets/home/kontaktparty-banner-2000.webp";

const renderHome = () =>
  renderWithProviders(
    <UserContext.Provider value={{ user: undefined, isLoading: false }}>
      <Home />
    </UserContext.Provider>,
  );

describe("Home", () => {
  it("shows the bundled Kontaktparty banner in every width", () => {
    renderHome();

    const banner = screen.getByRole("img", { name: "home.kp.image_alt" });

    expect(banner.getAttribute("src")).toBe(banner1200);
    expect(banner.getAttribute("srcset")).toBe(
      `${banner800} 800w, ${banner1200} 1200w, ${banner2000} 2000w`,
    );
    expect(banner.getAttribute("sizes")).toBeTruthy();
    expect(banner.getAttribute("src")).not.toContain("placehold.co");
  });

  it("reserves the banner's own aspect ratio", () => {
    renderHome();

    const banner = screen.getByRole("img", { name: "home.kp.image_alt" });

    expect(banner.getAttribute("width")).toBe("2000");
    expect(banner.getAttribute("height")).toBe("626");
  });
});
