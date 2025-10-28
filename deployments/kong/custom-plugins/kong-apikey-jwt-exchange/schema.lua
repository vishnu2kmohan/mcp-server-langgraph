--[[
Kong API Key JWT Exchange Plugin Schema

Defines configuration schema for the plugin.
--]]

local typedefs = require "kong.db.schema.typedefs"

return {
  name = "kong-apikey-jwt-exchange",
  fields = {
    {
      config = {
        type = "record",
        fields = {
          {
            mcp_server_url = {
              type = "string",
              required = true,
              default = "http://mcp-server-langgraph:80",
              description = "Base URL of MCP server for validation endpoint",
            }
          },
          {
            cache_ttl = {
              type = "number",
              required = false,
              default = 300,
              description = "Cache TTL in seconds for API key -> JWT mapping (default: 300)",
            }
          },
          {
            timeout = {
              type = "number",
              required = false,
              default = 5000,
              description = "Timeout for MCP validation call in milliseconds (default: 5000)",
            }
          },
          {
            api_key_headers = {
              type = "array",
              required = false,
              default = { "apikey", "x-api-key" },
              elements = { type = "string" },
              description = "List of headers to check for API key (default: ['apikey', 'x-api-key'])",
            }
          },
        },
      },
    },
  },
}
