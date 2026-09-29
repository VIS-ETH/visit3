import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Button } from "@mantine/core";
import { screen } from "@testing-library/react";
import RepickableFileButton from "../../components/RepickableFileButton";
import UploadFileInput from "../../components/UploadFileInput";
import { renderWithProviders } from "../render";

const PICK = "test.pick_file";

let openFileDialog: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  openFileDialog = vi.spyOn(HTMLInputElement.prototype, "click");
});

afterEach(() => {
  openFileDialog.mockRestore();
});

describe("uploads without the unavailable flag", () => {
  it("opens the file dialog of a file button", async () => {
    const { user } = renderWithProviders(
      <RepickableFileButton onChange={vi.fn()}>
        {(props) => <Button {...props}>{PICK}</Button>}
      </RepickableFileButton>,
    );

    await user.click(screen.getByRole("button", { name: PICK }));

    expect(openFileDialog).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByText("uploads.unavailable_title"),
    ).not.toBeInTheDocument();
  });

  it("opens the file dialog of a file input", async () => {
    const { user } = renderWithProviders(
      <UploadFileInput placeholder={PICK} onChange={vi.fn()} />,
    );

    await user.click(screen.getByRole("button", { name: PICK }));

    expect(openFileDialog).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByText("uploads.unavailable_title"),
    ).not.toBeInTheDocument();
  });
});
