/**
 * Schema Form Utilities Tests
 *
 * Tests for JSON Schema to form field parsing utilities.
 */

import { describe, it, expect } from "vitest";
import {
  parseSchemaToFields,
  getInputType,
  type JSONSchema,
} from "./schemaForm";

describe("schemaForm", () => {
  describe("parseSchemaToFields", () => {
    it("should return empty array for schema without properties", () => {
      const schema: JSONSchema = {};
      expect(parseSchemaToFields(schema)).toEqual([]);
    });

    it("should parse simple string properties", () => {
      const schema: JSONSchema = {
        properties: {
          name: { type: "string", description: "User name" },
        },
      };

      const fields = parseSchemaToFields(schema);

      expect(fields).toHaveLength(1);
      expect(fields[0]).toEqual({
        name: "name",
        type: "string",
        description: "User name",
        required: false,
        defaultValue: undefined,
      });
    });

    it("should mark required fields", () => {
      const schema: JSONSchema = {
        properties: {
          email: { type: "string" },
          nickname: { type: "string" },
        },
        required: ["email"],
      };

      const fields = parseSchemaToFields(schema);

      expect(fields).toHaveLength(2);
      const emailField = fields.find((f) => f.name === "email");
      const nicknameField = fields.find((f) => f.name === "nickname");

      expect(emailField?.required).toBe(true);
      expect(nicknameField?.required).toBe(false);
    });

    it("should include default values", () => {
      const schema: JSONSchema = {
        properties: {
          count: { type: "integer", default: 10 },
        },
      };

      const fields = parseSchemaToFields(schema);

      expect(fields[0].defaultValue).toBe(10);
    });

    it("should handle multiple property types", () => {
      const schema: JSONSchema = {
        properties: {
          name: { type: "string" },
          age: { type: "integer" },
          score: { type: "number" },
          active: { type: "boolean" },
        },
      };

      const fields = parseSchemaToFields(schema);

      expect(fields).toHaveLength(4);
      expect(fields.find((f) => f.name === "name")?.type).toBe("string");
      expect(fields.find((f) => f.name === "age")?.type).toBe("integer");
      expect(fields.find((f) => f.name === "score")?.type).toBe("number");
      expect(fields.find((f) => f.name === "active")?.type).toBe("boolean");
    });

    it("should default type to string when not specified", () => {
      const schema: JSONSchema = {
        properties: {
          unknown: {},
        },
      };

      const fields = parseSchemaToFields(schema);

      expect(fields[0].type).toBe("string");
    });
  });

  describe("getInputType", () => {
    it('should return "number" for number type', () => {
      expect(getInputType("number")).toBe("number");
    });

    it('should return "number" for integer type', () => {
      expect(getInputType("integer")).toBe("number");
    });

    it('should return "checkbox" for boolean type', () => {
      expect(getInputType("boolean")).toBe("checkbox");
    });

    it('should return "text" for string type', () => {
      expect(getInputType("string")).toBe("text");
    });

    it('should return "text" for unknown types', () => {
      expect(getInputType("object")).toBe("text");
      expect(getInputType("array")).toBe("text");
      expect(getInputType("unknown")).toBe("text");
    });
  });
});
