# ServicePrincipalResponse

Response containing service principal details

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

## Example

```typescript
import { ServicePrincipalResponse } from 'mcp-client';

const instance: ServicePrincipalResponse = {
    service_id,
    name,
    description,
    authentication_mode,
    associated_user_id,
    owner_user_id,
    inherit_permissions,
    enabled,
    created_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
