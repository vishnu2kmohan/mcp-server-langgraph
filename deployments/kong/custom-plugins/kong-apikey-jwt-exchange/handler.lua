--[[
Kong API Key to JWT Exchange Plugin

Intercepts requests with API keys and exchanges them for JWTs by calling
the MCP Server validation endpoint. Caches valid API key→JWT mappings
for performance.

See ADR-0034 for architecture details.

Configuration:
  - mcp_server_url: URL to MCP server validation endpoint
  - cache_ttl: Cache TTL in seconds (default: 300)
  - api_key_headers: Headers to check for API key (default: ["apikey", "x-api-key"])
--]]

local http = require "resty.http"
local cjson = require "cjson"

local ApiKeyJwtExchangeHandler = {
  VERSION = "1.0.0",
  PRIORITY = 1000,  -- Execute before JWT plugin (which has priority 1005)
}

-- Helper function to get API key from request headers
local function get_api_key(conf)
  for _, header_name in ipairs(conf.api_key_headers) do
    local api_key = kong.request.get_header(header_name)
    if api_key then
      return api_key, header_name
    end
  end
  return nil, nil
end

-- Helper function to call MCP server validation endpoint
local function validate_api_key_with_mcp(api_key, conf)
  local httpc = http.new()
  httpc:set_timeout(conf.timeout or 5000)  -- 5 second timeout

  local validation_url = conf.mcp_server_url .. "/api/v1/api-keys/validate"

  kong.log.debug("Validating API key with MCP server: ", validation_url)

  local res, err = httpc:request_uri(validation_url, {
    method = "POST",
    headers = {
      ["Content-Type"] = "application/json",
      ["X-API-Key"] = api_key,
    },
    ssl_verify = false,  -- In production, set to true with proper certs
  })

  if not res then
    kong.log.err("Failed to call MCP validation endpoint: ", err)
    return nil, "Failed to validate API key: " .. (err or "unknown error")
  end

  if res.status ~= 200 then
    kong.log.warn("MCP validation failed with status: ", res.status)
    return nil, "Invalid or expired API key"
  end

  local ok, data = pcall(cjson.decode, res.body)
  if not ok then
    kong.log.err("Failed to parse MCP response: ", data)
    return nil, "Invalid response from validation service"
  end

  return data, nil
end

-- Access phase: Intercept request and exchange API key for JWT
function ApiKeyJwtExchangeHandler:access(conf)
  -- 1. Check if request has API key
  local api_key, header_name = get_api_key(conf)

  if not api_key then
    -- No API key found, let other auth plugins handle it
    kong.log.debug("No API key found in request headers")
    return
  end

  kong.log.info("Found API key in header: ", header_name)

  -- 2. Check cache first (using MD5 hash of API key as cache key)
  local cache_key = "apikey:" .. ngx.md5(api_key)
  local cached_jwt, err = kong.cache:get(cache_key, nil, function()
    return nil  -- Will be populated below if valid
  end)

  if cached_jwt then
    kong.log.debug("Using cached JWT for API key")

    -- Replace API key with cached JWT
    kong.service.request.clear_header(header_name)
    kong.service.request.set_header("Authorization", "Bearer " .. cached_jwt)

    -- Store user info in context for logging
    kong.ctx.shared.authenticated_by = "api-key-cache"

    return
  end

  -- 3. Validate API key with MCP server
  local validation_data, validation_err = validate_api_key_with_mcp(api_key, conf)

  if validation_err then
    kong.log.warn("API key validation failed: ", validation_err)
    return kong.response.exit(401, {
      message = validation_err
    })
  end

  local jwt = validation_data.access_token
  if not jwt then
    kong.log.err("No access_token in validation response")
    return kong.response.exit(500, {
      message = "Invalid validation response"
    })
  end

  -- 4. Cache the JWT (with configured TTL)
  local cache_ttl = conf.cache_ttl or 300  -- Default 5 minutes
  local ok, cache_err = kong.cache:set(cache_key, jwt, cache_ttl)

  if not ok then
    kong.log.warn("Failed to cache JWT: ", cache_err)
    -- Continue anyway, just won't be cached
  else
    kong.log.debug("Cached JWT with TTL: ", cache_ttl, " seconds")
  end

  -- 5. Replace API key header with JWT
  kong.service.request.clear_header(header_name)
  kong.service.request.set_header("Authorization", "Bearer " .. jwt)

  -- 6. Store authentication metadata in context
  kong.ctx.shared.authenticated_by = "api-key-exchange"
  kong.ctx.shared.user_id = validation_data.user_id
  kong.ctx.shared.username = validation_data.username

  kong.log.info("Successfully exchanged API key for JWT (user: ", validation_data.username, ")")
end

-- Header filter phase: Add custom headers to response if needed
function ApiKeyJwtExchangeHandler:header_filter(conf)
  if kong.ctx.shared.authenticated_by == "api-key-exchange" or
     kong.ctx.shared.authenticated_by == "api-key-cache" then
    -- Optionally add header to indicate auth method
    kong.response.set_header("X-Auth-Method", kong.ctx.shared.authenticated_by)
  end
end

return ApiKeyJwtExchangeHandler
