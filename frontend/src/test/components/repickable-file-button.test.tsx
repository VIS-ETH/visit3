import { describe, expect, it, vi } from "vitest";
import { Button } from "@mantine/core";
import { File as NodeFile } from "node:buffer";
import RepickableFileButton from "../../components/RepickableFileButton";
import { renderWithProviders } from "../render";

const createFile = () =>
  new NodeFile(["bytes"], "plan.pdf", {
    type: "application/pdf",
  }) as unknown as File;

describe("the repickable file button", () => {
  it("reports the same file every time it is picked", async () => {
    const onChange = vi.fn();
    const { user, container } = renderWithProviders(
      <RepickableFileButton onChange={onChange}>
        {(props) => <Button {...props} />}
      </RepickableFileButton>,
    );
    const input =
      container.querySelector<HTMLInputElement>('input[type="file"]')!;
    const file = createFile();

    await user.upload(input, file);
    await user.upload(input, file);

    expect(onChange).toHaveBeenCalledTimes(2);
    expect(onChange).toHaveBeenLastCalledWith(file);
    expect(input.value).toBe("");
  });
});
