# CreateServicePrincipalRequest

Request to create a new service principal

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** | Human-readable name for the service | [default to undefined]
**description** | **string** | Purpose/description of the service | [default to undefined]
**authentication_mode** | **string** | Authentication mode: \&#39;client_credentials\&#39; or \&#39;service_account_user\&#39; | [optional] [default to 'client_credentials']
**associated_user_id** | **string** |  | [optional] [default to undefined]
**inherit_permissions** | **boolean** | Whether to inherit permissions from associated user | [optional] [default to false]

## Example

```typescript
import { CreateServicePrincipalRequest } from 'mcp-client';

const instance: CreateServicePrincipalRequest = {
    name,
    description,
    authentication_mode,
    associated_user_id,
    inherit_permissions,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
