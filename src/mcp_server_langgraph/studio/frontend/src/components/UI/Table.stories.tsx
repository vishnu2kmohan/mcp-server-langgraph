import type { Meta, StoryObj } from "@storybook/react-vite";
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from "./Table";

const meta: Meta<typeof Table> = {
  title: "UI/Table",
  component: Table,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
};

export default meta;
type Story = StoryObj<typeof Table>;

const sampleData = [
  { name: "Widget A", category: "Hardware", price: 29.99, stock: 150 },
  { name: "Widget B", category: "Software", price: 49.99, stock: 75 },
  { name: "Widget C", category: "Hardware", price: 19.99, stock: 200 },
  { name: "Widget D", category: "Services", price: 99.99, stock: 50 },
];

export const Default: Story = {
  render: () => (
    <Table>
      <TableHead>
        <TableRow>
          <TableHeaderCell>Name</TableHeaderCell>
          <TableHeaderCell>Category</TableHeaderCell>
          <TableHeaderCell align="right">Price</TableHeaderCell>
          <TableHeaderCell align="right">Stock</TableHeaderCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {sampleData.map((item) => (
          <TableRow key={item.name}>
            <TableCell>{item.name}</TableCell>
            <TableCell>{item.category}</TableCell>
            <TableCell align="right">${item.price.toFixed(2)}</TableCell>
            <TableCell align="right">{item.stock}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ),
};

export const Striped: Story = {
  render: () => (
    <Table striped>
      <TableHead>
        <TableRow>
          <TableHeaderCell>Name</TableHeaderCell>
          <TableHeaderCell>Category</TableHeaderCell>
          <TableHeaderCell align="right">Price</TableHeaderCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {sampleData.map((item) => (
          <TableRow key={item.name}>
            <TableCell>{item.name}</TableCell>
            <TableCell>{item.category}</TableCell>
            <TableCell align="right">${item.price.toFixed(2)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ),
};

export const Hoverable: Story = {
  render: () => (
    <Table hoverable>
      <TableHead>
        <TableRow>
          <TableHeaderCell>Name</TableHeaderCell>
          <TableHeaderCell>Category</TableHeaderCell>
          <TableHeaderCell align="right">Price</TableHeaderCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {sampleData.map((item) => (
          <TableRow key={item.name}>
            <TableCell>{item.name}</TableCell>
            <TableCell>{item.category}</TableCell>
            <TableCell align="right">${item.price.toFixed(2)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ),
};

export const Compact: Story = {
  render: () => (
    <Table size="compact">
      <TableHead>
        <TableRow>
          <TableHeaderCell>Name</TableHeaderCell>
          <TableHeaderCell>Category</TableHeaderCell>
          <TableHeaderCell align="right">Price</TableHeaderCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {sampleData.map((item) => (
          <TableRow key={item.name}>
            <TableCell>{item.name}</TableCell>
            <TableCell>{item.category}</TableCell>
            <TableCell align="right">${item.price.toFixed(2)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ),
};

export const AllVariants: Story = {
  render: () => (
    <Table striped hoverable bordered>
      <TableHead>
        <TableRow>
          <TableHeaderCell>Name</TableHeaderCell>
          <TableHeaderCell>Category</TableHeaderCell>
          <TableHeaderCell align="right">Price</TableHeaderCell>
          <TableHeaderCell align="right">Stock</TableHeaderCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {sampleData.map((item) => (
          <TableRow key={item.name}>
            <TableCell>{item.name}</TableCell>
            <TableCell>{item.category}</TableCell>
            <TableCell align="right">${item.price.toFixed(2)}</TableCell>
            <TableCell align="right">{item.stock}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ),
};
