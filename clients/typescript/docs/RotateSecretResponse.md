# RotateSecretResponse

Response when rotating service principal secret

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**service_id** | **string** |  | [default to undefined]
**client_secret** | **string** | New client secret | [default to undefined]
**message** | **string** |  | [optional] [default to 'Secret rotated successfully. Update your service configuration.']

## Example

```typescript
import { RotateSecretResponse } from 'mcp-client';

const instance: RotateSecretResponse = {
    service_id,
    client_secret,
    message,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
