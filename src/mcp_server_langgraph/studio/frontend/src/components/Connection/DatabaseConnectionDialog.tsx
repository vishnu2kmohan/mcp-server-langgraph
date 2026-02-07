/**
 * DatabaseConnectionDialog Component
 *
 * Dialog for creating and editing database connections.
 * Supports direct credentials and secret reference methods.
 * Uses CVA, Radix colors, and semantic Button variants per STYLE.md.
 *
 * @see SQLGlot Phase 6
 */

import { useState, useEffect, useCallback } from "react";
import type {
  DatabaseDialect,
  SSLMode,
  ConnectionMethod,
  ConnectionScope,
  DatabaseConnectionCreate,
  DatabaseConnectionCamelCase,
} from "../../types/connection";
import { Dialog } from "../UI/Dialog";
import {
  Button,
  Input,
  Select,
  RadioGroup,
  Radio,
  SelectionCard,
} from "@/components/UI";
import { ScopeSelector } from "./ScopeSelector";
import { Database, CheckCircle, AlertCircle } from "lucide-react";
import { cn } from "../../utils/cn"; // Used for test result styling

// Dialect options with labels and default ports
const DIALECTS: { id: DatabaseDialect; label: string; defaultPort: number }[] =
  [
    { id: "postgres", label: "PostgreSQL", defaultPort: 5432 },
    { id: "mysql", label: "MySQL", defaultPort: 3306 },
    { id: "sqlite", label: "SQLite", defaultPort: 0 },
    { id: "bigquery", label: "BigQuery", defaultPort: 443 },
    { id: "snowflake", label: "Snowflake", defaultPort: 443 },
    { id: "duckdb", label: "DuckDB", defaultPort: 0 },
    { id: "redshift", label: "Redshift", defaultPort: 5439 },
    { id: "clickhouse", label: "ClickHouse", defaultPort: 8123 },
    { id: "trino", label: "Trino", defaultPort: 8080 },
  ];

const SSL_MODES: { id: SSLMode; label: string }[] = [
  { id: "disable", label: "Disabled" },
  { id: "require", label: "Required" },
  { id: "verify-ca", label: "Verify CA" },
  { id: "verify-full", label: "Verify Full" },
];

// Dialects that don't require host/port (file-based or cloud-managed)
const HOSTLESS_DIALECTS: DatabaseDialect[] = ["bigquery", "duckdb", "sqlite"];

interface TestResult {
  success: boolean;
  error?: string;
}

interface DatabaseConnectionDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog should close */
  onClose: () => void;
  /** Callback when form is submitted */
  onSubmit: (data: DatabaseConnectionCreate) => Promise<void>;
  /** Existing connection for edit mode */
  connection?: DatabaseConnectionCamelCase;
  /** Project ID for scoped connections */
  projectId?: string;
}

interface FormErrors {
  name?: string;
  host?: string;
  database?: string;
  username?: string;
  password?: string;
  secretPath?: string;
  secretKey?: string;
  projectId?: string;
  accountId?: string;
}

export function DatabaseConnectionDialog({
  open,
  onClose,
  onSubmit,
  connection,
  projectId: _projectId,
}: DatabaseConnectionDialogProps) {
  const isEditing = !!connection;

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [dialect, setDialect] = useState<DatabaseDialect>("postgres");
  const [connectionMethod, setConnectionMethod] =
    useState<ConnectionMethod>("credentials");
  const [host, setHost] = useState("");
  const [port, setPort] = useState<number>(5432);
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [secretPath, setSecretPath] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [sslMode, setSslMode] = useState<SSLMode>("require");
  const [scope, setScope] = useState<ConnectionScope>("user");
  // Cloud-specific
  const [cloudProjectId, setCloudProjectId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");

  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      if (connection) {
        setName(connection.name);
        setDescription(connection.description || "");
        setDialect(connection.dialect as DatabaseDialect);
        setHost(connection.host || "");
        setPort(connection.port || 5432);
        setDatabase(connection.database || "");
        setSslMode((connection.sslMode || "require") as SSLMode);
      } else {
        setName("");
        setDescription("");
        setDialect("postgres");
        setConnectionMethod("credentials");
        setHost("");
        setPort(5432);
        setDatabase("");
        setUsername("");
        setPassword("");
        setSecretPath("");
        setSecretKey("");
        setSslMode("require");
        setScope("user");
        setCloudProjectId("");
        setAccountId("");
        setWarehouseId("");
      }
      setErrors({});
      setTestResult(null);
    }
  }, [open, connection]);

  // Update port when dialect changes
  useEffect(() => {
    const dialectInfo = DIALECTS.find((d) => d.id === dialect);
    if (dialectInfo && !isEditing) {
      setPort(dialectInfo.defaultPort);
    }
  }, [dialect, isEditing]);

  const requiresHost = !HOSTLESS_DIALECTS.includes(dialect);

  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) {
      newErrors.name = "Name is required";
    }

    if (connectionMethod === "credentials") {
      if (requiresHost && !host.trim()) {
        newErrors.host = "Host is required";
      }
      if (dialect === "bigquery" && !cloudProjectId.trim()) {
        newErrors.projectId = "Project ID is required for BigQuery";
      }
      if (dialect === "snowflake" && !accountId.trim()) {
        newErrors.accountId = "Account ID is required for Snowflake";
      }
    } else if (connectionMethod === "secret_ref") {
      if (!secretPath.trim()) {
        newErrors.secretPath = "Secret path is required";
      }
      if (!secretKey.trim()) {
        newErrors.secretKey = "Secret key is required";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [
    name,
    connectionMethod,
    requiresHost,
    host,
    dialect,
    cloudProjectId,
    accountId,
    secretPath,
    secretKey,
  ]);

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const data: DatabaseConnectionCreate = {
        name,
        description: description || null,
        dialect,
        connectionMethod,
        sslMode,
        scope,
      };

      if (connectionMethod === "credentials") {
        if (requiresHost) {
          data.host = host;
          data.port = port;
        }
        data.database = database || null;
        data.username = username || null;
        data.password = password || null;
        if (dialect === "bigquery") {
          data.projectId = cloudProjectId || null;
        }
        if (dialect === "snowflake") {
          data.accountId = accountId || null;
          data.warehouseId = warehouseId || null;
        }
      } else if (connectionMethod === "secret_ref") {
        data.secretPath = secretPath;
        data.secretKey = secretKey;
      }

      await onSubmit(data);
      onClose();
    } catch (error) {
      console.error("Failed to save database connection:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const footerContent = (
    <>
      <Button
        variant="secondary"
        onClick={onClose}
        disabled={isSubmitting}
        data-testid="cancel-button"
      >
        Cancel
      </Button>
      <Button
        variant="primary"
        onClick={handleSubmit}
        disabled={isSubmitting}
        data-testid="submit-button"
      >
        {isSubmitting ? "Saving..." : isEditing ? "Save" : "Create"}
      </Button>
    </>
  );

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={isEditing ? "Edit Database Connection" : "New Database Connection"}
      footer={footerContent}
    >
      <div className="space-y-6">
        {/* Connection Name */}
        <div className="space-y-1">
          <label
            htmlFor="db-name"
            className="text-sm font-medium text-neutral-12"
          >
            Name <span className="text-error-9">*</span>
          </label>
          <Input
            id="db-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Production Database"
            data-testid="input-name"
          />
          {errors.name && (
            <p className="text-xs text-error-11" role="alert">
              {errors.name}
            </p>
          )}
        </div>

        {/* Description */}
        <div className="space-y-1">
          <label
            htmlFor="db-description"
            className="text-sm font-medium text-neutral-12"
          >
            Description
          </label>
          <Input
            id="db-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            data-testid="input-description"
          />
        </div>

        {/* Dialect Selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-neutral-12">
            Database Type <span className="text-error-9">*</span>
          </label>
          <div className="grid grid-cols-3 gap-2">
            {DIALECTS.map((d) => (
              <SelectionCard
                key={d.id}
                title={d.label}
                icon={<Database className="h-4 w-4" />}
                selected={dialect === d.id}
                onClick={() => setDialect(d.id)}
                ariaLabel={`Select ${d.label} database`}
                className="p-2 text-sm"
                data-testid={`dialect-${d.id}`}
              />
            ))}
          </div>
        </div>

        {/* Connection Method */}
        <div className="space-y-2">
          <RadioGroup
            name="connectionMethod"
            value={connectionMethod}
            onChange={(value) => setConnectionMethod(value as ConnectionMethod)}
            legend="Credential Source"
            orientation="horizontal"
          >
            <Radio
              value="credentials"
              label="Enter credentials directly"
              data-testid="method-credentials"
            />
            <Radio
              value="secret_ref"
              label="Reference existing secret"
              data-testid="method-secret-ref"
            />
          </RadioGroup>
        </div>

        {/* Credential Fields */}
        {connectionMethod === "credentials" && (
          <div className="space-y-4">
            {requiresHost && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label
                    htmlFor="db-host"
                    className="text-sm font-medium text-neutral-12"
                  >
                    Host <span className="text-error-9">*</span>
                  </label>
                  <Input
                    id="db-host"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    placeholder="db.example.com"
                    data-testid="input-host"
                  />
                  {errors.host && (
                    <p className="text-xs text-error-11" role="alert">
                      {errors.host}
                    </p>
                  )}
                </div>
                <div className="space-y-1">
                  <label
                    htmlFor="db-port"
                    className="text-sm font-medium text-neutral-12"
                  >
                    Port
                  </label>
                  <Input
                    id="db-port"
                    type="number"
                    value={port}
                    onChange={(e) => setPort(parseInt(e.target.value) || 0)}
                    data-testid="input-port"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label
                htmlFor="db-database"
                className="text-sm font-medium text-neutral-12"
              >
                Database
              </label>
              <Input
                id="db-database"
                value={database}
                onChange={(e) => setDatabase(e.target.value)}
                placeholder="my_database"
                data-testid="input-database"
              />
            </div>

            {/* Cloud-specific fields */}
            {dialect === "bigquery" && (
              <div className="space-y-1">
                <label
                  htmlFor="db-project-id"
                  className="text-sm font-medium text-neutral-12"
                >
                  GCP Project ID <span className="text-error-9">*</span>
                </label>
                <Input
                  id="db-project-id"
                  value={cloudProjectId}
                  onChange={(e) => setCloudProjectId(e.target.value)}
                  placeholder="my-gcp-project"
                  data-testid="input-project-id"
                />
                {errors.projectId && (
                  <p className="text-xs text-error-11" role="alert">
                    {errors.projectId}
                  </p>
                )}
              </div>
            )}

            {dialect === "snowflake" && (
              <>
                <div className="space-y-1">
                  <label
                    htmlFor="db-account-id"
                    className="text-sm font-medium text-neutral-12"
                  >
                    Account ID <span className="text-error-9">*</span>
                  </label>
                  <Input
                    id="db-account-id"
                    value={accountId}
                    onChange={(e) => setAccountId(e.target.value)}
                    placeholder="xy12345.us-east-1"
                    data-testid="input-account-id"
                  />
                  {errors.accountId && (
                    <p className="text-xs text-error-11" role="alert">
                      {errors.accountId}
                    </p>
                  )}
                </div>
                <div className="space-y-1">
                  <label
                    htmlFor="db-warehouse-id"
                    className="text-sm font-medium text-neutral-12"
                  >
                    Warehouse
                  </label>
                  <Input
                    id="db-warehouse-id"
                    value={warehouseId}
                    onChange={(e) => setWarehouseId(e.target.value)}
                    placeholder="COMPUTE_WH"
                    data-testid="input-warehouse-id"
                  />
                </div>
              </>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label
                  htmlFor="db-username"
                  className="text-sm font-medium text-neutral-12"
                >
                  Username
                </label>
                <Input
                  id="db-username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  data-testid="input-username"
                />
              </div>
              <div className="space-y-1">
                <label
                  htmlFor="db-password"
                  className="text-sm font-medium text-neutral-12"
                >
                  Password
                </label>
                <Input
                  id="db-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  data-testid="input-password"
                />
              </div>
            </div>
          </div>
        )}

        {/* Secret Reference Fields */}
        {connectionMethod === "secret_ref" && (
          <div className="space-y-4">
            <div className="space-y-1">
              <label
                htmlFor="db-secret-path"
                className="text-sm font-medium text-neutral-12"
              >
                Secret Path <span className="text-error-9">*</span>
              </label>
              <Input
                id="db-secret-path"
                value={secretPath}
                onChange={(e) => setSecretPath(e.target.value)}
                placeholder="/database/production/postgres"
                data-testid="input-secret-path"
              />
              {errors.secretPath && (
                <p className="text-xs text-error-11" role="alert">
                  {errors.secretPath}
                </p>
              )}
            </div>
            <div className="space-y-1">
              <label
                htmlFor="db-secret-key"
                className="text-sm font-medium text-neutral-12"
              >
                Secret Key <span className="text-error-9">*</span>
              </label>
              <Input
                id="db-secret-key"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                placeholder="CONNECTION_STRING"
                data-testid="input-secret-key"
              />
              {errors.secretKey && (
                <p className="text-xs text-error-11" role="alert">
                  {errors.secretKey}
                </p>
              )}
            </div>
          </div>
        )}

        {/* SSL Mode */}
        <div className="space-y-1">
          <label
            htmlFor="db-ssl-mode"
            className="text-sm font-medium text-neutral-12"
          >
            SSL Mode
          </label>
          <Select
            id="db-ssl-mode"
            value={sslMode}
            onChange={(e) => setSslMode(e.target.value as SSLMode)}
            options={SSL_MODES.map((mode) => ({
              value: mode.id,
              label: mode.label,
            }))}
            data-testid="select-ssl-mode"
          />
        </div>

        {/* Scope Selector */}
        <ScopeSelector value={scope} onChange={setScope} />

        {/* Test Result Feedback */}
        {testResult && (
          <div
            role="alert"
            className={cn(
              "p-3 rounded-lg flex items-center gap-2",
              testResult.success
                ? "bg-success-2 border border-success-6 text-success-11"
                : "bg-error-2 border border-error-6 text-error-11",
            )}
            data-testid="test-result"
          >
            {testResult.success ? (
              <>
                <CheckCircle className="h-4 w-4" aria-hidden="true" />
                Connection successful
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4" aria-hidden="true" />
                {testResult.error || "Connection failed"}
              </>
            )}
          </div>
        )}
      </div>
    </Dialog>
  );
}
