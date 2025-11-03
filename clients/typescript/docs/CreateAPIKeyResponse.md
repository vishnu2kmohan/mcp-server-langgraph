# CreateAPIKeyResponse

Response when creating API key (includes the key itself)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key_id** | **string** |  | [default to undefined]
**name** | **string** |  | [default to undefined]
**created** | **string** |  | [default to undefined]
**expires_at** | **string** |  | [default to undefined]
**last_used** | **string** |  | [optional] [default to undefined]
**api_key** | **string** | API key (save securely, won\&#39;t be shown again) | [default to undefined]
**message** | **string** |  | [optional] [default to 'API key created successfully. Save it securely - it will not be shown again.']

## Example

```typescript
import { CreateAPIKeyResponse } from 'mcp-client';

const instance: CreateAPIKeyResponse = {
    key_id,
    name,
    created,
    expires_at,
    last_used,
    api_key,
    message,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
