# RotateAPIKeyResponse

Response when rotating API key

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key_id** | **string** |  | [default to undefined]
**new_api_key** | **string** | New API key | [default to undefined]
**message** | **string** |  | [optional] [default to 'API key rotated successfully. Update your client configuration.']

## Example

```typescript
import { RotateAPIKeyResponse } from 'mcp-client';

const instance: RotateAPIKeyResponse = {
    key_id,
    new_api_key,
    message,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
