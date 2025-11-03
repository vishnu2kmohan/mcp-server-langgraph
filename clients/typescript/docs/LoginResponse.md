# LoginResponse

Login response with JWT token

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**access_token** | **string** | JWT access token | [default to undefined]
**token_type** | **string** | Token type (always \&#39;bearer\&#39;) | [optional] [default to 'bearer']
**expires_in** | **number** | Token expiration in seconds | [default to undefined]
**user_id** | **string** | User identifier | [default to undefined]
**username** | **string** | Username | [default to undefined]
**roles** | **Array&lt;string&gt;** | User roles | [default to undefined]

## Example

```typescript
import { LoginResponse } from 'mcp-client';

const instance: LoginResponse = {
    access_token,
    token_type,
    expires_in,
    user_id,
    username,
    roles,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
