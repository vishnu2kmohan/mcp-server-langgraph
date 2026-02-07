/**
 * DatabaseConnectionDialog Tests
 *
 * Tests for the database connection dialog component covering:
 * - Dialog visibility and titles
 * - Dialect selection grid
 * - Credential method switching
 * - Form validation (required fields)
 * - Cloud-specific fields (BigQuery, Snowflake)
 * - Secret reference fields
 * - Form submission
 * - SSL mode selector
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DatabaseConnectionDialog } from "./DatabaseConnectionDialog";

// Mock ScopeSelector to avoid complexity
vi.mock("./ScopeSelector", () => ({
  ScopeSelector: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (v: string) => void;
  }) => (
    <select
      data-testid="scope-selector"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="user">User</option>
      <option value="project">Project</option>
    </select>
  ),
}));

describe("DatabaseConnectionDialog", () => {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    onSubmit: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("renders when open", () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    expect(screen.getByText("New Database Connection")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(<DatabaseConnectionDialog {...defaultProps} open={false} />);
    expect(
      screen.queryByText("New Database Connection"),
    ).not.toBeInTheDocument();
  });

  it("shows edit title when editing", () => {
    const connection = {
      id: "test-id",
      name: "Test DB",
      description: null,
      dialect: "postgres",
      host: "localhost",
      port: 5432,
      database: "testdb",
      projectId: null,
      accountId: null,
      warehouseId: null,
      sslMode: "require",
      status: "disconnected",
      lastTestedAt: null,
      dialectVersion: null,
      ownerId: "user1",
      tenantId: "tenant1",
      createdAt: "2026-01-01",
      updatedAt: "2026-01-01",
    };
    render(
      <DatabaseConnectionDialog {...defaultProps} connection={connection} />,
    );
    expect(screen.getByText("Edit Database Connection")).toBeInTheDocument();
  });

  it("renders all dialect options", () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    expect(screen.getByTestId("dialect-postgres")).toBeInTheDocument();
    expect(screen.getByTestId("dialect-mysql")).toBeInTheDocument();
    expect(screen.getByTestId("dialect-sqlite")).toBeInTheDocument();
    expect(screen.getByTestId("dialect-bigquery")).toBeInTheDocument();
    expect(screen.getByTestId("dialect-snowflake")).toBeInTheDocument();
    expect(screen.getByTestId("dialect-duckdb")).toBeInTheDocument();
    expect(screen.getByTestId("dialect-redshift")).toBeInTheDocument();
    expect(screen.getByTestId("dialect-clickhouse")).toBeInTheDocument();
    expect(screen.getByTestId("dialect-trino")).toBeInTheDocument();
  });

  it("shows host/port fields for server-based dialects", () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    // postgres is default, requires host
    expect(screen.getByTestId("input-host")).toBeInTheDocument();
    expect(screen.getByTestId("input-port")).toBeInTheDocument();
  });

  it("shows credential method radio buttons", () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    expect(screen.getByTestId("method-credentials")).toBeInTheDocument();
    expect(screen.getByTestId("method-secret-ref")).toBeInTheDocument();
  });

  it("validates name is required", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.click(screen.getByTestId("submit-button"));
    expect(screen.getByText("Name is required")).toBeInTheDocument();
    expect(defaultProps.onSubmit).not.toHaveBeenCalled();
  });

  it("validates host is required for server dialects", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.type(screen.getByTestId("input-name"), "Test DB");
    await userEvent.click(screen.getByTestId("submit-button"));
    expect(screen.getByText("Host is required")).toBeInTheDocument();
  });

  it("shows secret ref fields when method is secret_ref", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.click(screen.getByTestId("method-secret-ref"));
    expect(screen.getByTestId("input-secret-path")).toBeInTheDocument();
    expect(screen.getByTestId("input-secret-key")).toBeInTheDocument();
  });

  it("shows BigQuery project ID field when BigQuery selected", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.click(screen.getByTestId("dialect-bigquery"));
    expect(screen.getByTestId("input-project-id")).toBeInTheDocument();
  });

  it("shows Snowflake fields when Snowflake selected", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.click(screen.getByTestId("dialect-snowflake"));
    expect(screen.getByTestId("input-account-id")).toBeInTheDocument();
    expect(screen.getByTestId("input-warehouse-id")).toBeInTheDocument();
  });

  it("submits valid form data", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.type(screen.getByTestId("input-name"), "My Database");
    await userEvent.type(screen.getByTestId("input-host"), "db.example.com");
    await userEvent.type(screen.getByTestId("input-database"), "mydb");
    await userEvent.click(screen.getByTestId("submit-button"));

    await waitFor(() => {
      expect(defaultProps.onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "My Database",
          dialect: "postgres",
          host: "db.example.com",
          database: "mydb",
        }),
      );
    });
  });

  it("calls onClose when cancel is clicked", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.click(screen.getByTestId("cancel-button"));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("has SSL mode selector", () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    expect(screen.getByTestId("select-ssl-mode")).toBeInTheDocument();
  });

  it("hides host/port for hostless dialects", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.click(screen.getByTestId("dialect-sqlite"));
    expect(screen.queryByTestId("input-host")).not.toBeInTheDocument();
    expect(screen.queryByTestId("input-port")).not.toBeInTheDocument();
  });

  it("validates secret path and key are required for secret_ref method", async () => {
    render(<DatabaseConnectionDialog {...defaultProps} />);
    await userEvent.type(screen.getByTestId("input-name"), "Test DB");
    await userEvent.click(screen.getByTestId("method-secret-ref"));
    await userEvent.click(screen.getByTestId("submit-button"));
    expect(screen.getByText("Secret path is required")).toBeInTheDocument();
    expect(screen.getByText("Secret key is required")).toBeInTheDocument();
  });
});
