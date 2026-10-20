import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import DataTable from "../../components/DataTable";
import { renderWithProviders } from "../render";

interface Row {
  name: string;
  price: number;
}

const rows: Row[] = [
  { name: "Table", price: 900 },
  { name: "Power", price: 12000 },
  { name: "Wifi", price: 2500 },
];

const renderTable = () =>
  renderWithProviders(
    <DataTable
      columns={[
        { key: "name", header: "Name", render: (row) => row.name },
        {
          key: "price",
          header: "Price",
          render: (row) => row.price,
          sortValue: (row) => row.price,
        },
      ]}
      data={rows}
      emptyLabel="empty"
      getRowKey={(row) => row.name}
    />,
  );

const names = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((row) => row.firstChild?.textContent);

describe("the data table", () => {
  it("sorts only the columns that define a sort value", async () => {
    const { user } = renderTable();

    expect(screen.queryByRole("button", { name: "Name" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Price" }));

    expect(names()).toEqual(["Table", "Wifi", "Power"]);

    await user.click(screen.getByRole("button", { name: "Price" }));

    expect(names()).toEqual(["Power", "Wifi", "Table"]);
  });
});
