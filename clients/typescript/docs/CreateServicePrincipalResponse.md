# CreateServicePrincipalResponse

Response when creating service principal (includes secret)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**service_id** | **string** |  | [default to undefined]
**name** | **string** |  | [default to undefined]
**description** | **string** |  | [default to undefined]
**authentication_mode** | **string** |  | [default to undefined]
**associated_user_id** | **string** |  | [default to undefined]
**owner_user_id** | **string** |  | [default to undefined]
**inherit_permissions** | **boolean** |  | [default to undefined]
**enabled** | **boolean** |  | [default to undefined]
**created_at** | **string** |  | [default to undefined]
**client_secret** | **string** | Client secret (save securely, won\&#39;t be shown again) | [default to undefined]
**message** | **string** |  | [optional] [default to 'Service principal created successfully. Save the client_secret securely.']

## Example

```typescript
import { CreateServicePrincipalResponse } from 'mcp-client';

const instance: CreateServicePrincipalResponse = {
    service_id,
    name,
    description,
    authentication_mode,
    associated_user_id,
    owner_user_id,
    inherit_permissions,
    enabled,
    created_at,
    client_secret,
    message,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
