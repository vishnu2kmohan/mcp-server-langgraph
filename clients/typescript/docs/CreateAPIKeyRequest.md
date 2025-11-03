# CreateAPIKeyRequest

Request to create a new API key

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** | Human-readable name for the API key | [default to undefined]
**expires_days** | **number** | Days until expiration (default: 365) | [optional] [default to 365]

## Example

```typescript
import { CreateAPIKeyRequest } from 'mcp-client';

const instance: CreateAPIKeyRequest = {
    name,
    expires_days,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
