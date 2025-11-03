# APIVersionInfo

API version metadata  Follows semantic versioning (MAJOR.MINOR.PATCH): - MAJOR: Breaking changes (incompatible API changes) - MINOR: New features (backward-compatible) - PATCH: Bug fixes (backward-compatible)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **string** | Application version (semantic versioning: MAJOR.MINOR.PATCH) | [default to undefined]
**api_version** | **string** | Current API version (e.g., \&#39;v1\&#39;) | [default to undefined]
**supported_versions** | **Array&lt;string&gt;** | List of supported API versions | [default to undefined]
**deprecated_versions** | **Array&lt;string&gt;** | List of deprecated API versions (still functional but will be removed) | [optional] [default to undefined]
**sunset_dates** | **{ [key: string]: string; }** | Sunset dates for deprecated versions (ISO 8601 format) | [optional] [default to undefined]
**changelog_url** | **string** |  | [optional] [default to undefined]
**documentation_url** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { APIVersionInfo } from 'mcp-client';

const instance: APIVersionInfo = {
    version,
    api_version,
    supported_versions,
    deprecated_versions,
    sunset_dates,
    changelog_url,
    documentation_url,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
