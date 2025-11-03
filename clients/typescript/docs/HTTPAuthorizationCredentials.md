# HTTPAuthorizationCredentials

The HTTP authorization credentials in the result of using `HTTPBearer` or `HTTPDigest` in a dependency.  The HTTP authorization header value is split by the first space.  The first part is the `scheme`, the second part is the `credentials`.  For example, in an HTTP Bearer token scheme, the client will send a header like:  ``` Authorization: Bearer deadbeef12346 ```  In this case:  * `scheme` will have the value `\"Bearer\"` * `credentials` will have the value `\"deadbeef12346\"`

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**scheme** | **string** |  | [default to undefined]
**credentials** | **string** |  | [default to undefined]

## Example

```typescript
import { HTTPAuthorizationCredentials } from 'mcp-client';

const instance: HTTPAuthorizationCredentials = {
    scheme,
    credentials,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
