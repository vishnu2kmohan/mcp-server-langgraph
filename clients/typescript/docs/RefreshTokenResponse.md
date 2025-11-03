# RefreshTokenResponse

Token refresh response

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**access_token** | **string** | New JWT access token | [default to undefined]
**token_type** | **string** | Token type | [optional] [default to 'bearer']
**expires_in** | **number** | Token expiration in seconds | [default to undefined]
**refresh_token** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { RefreshTokenResponse } from 'mcp-client';

const instance: RefreshTokenResponse = {
    access_token,
    token_type,
    expires_in,
    refresh_token,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
