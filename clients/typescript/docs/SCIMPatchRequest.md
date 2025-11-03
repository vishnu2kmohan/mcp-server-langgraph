# SCIMPatchRequest

SCIM PATCH request

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemas** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**Operations** | [**Array&lt;SCIMPatchOperation&gt;**](SCIMPatchOperation.md) |  | [default to undefined]

## Example

```typescript
import { SCIMPatchRequest } from 'mcp-client';

const instance: SCIMPatchRequest = {
    schemas,
    Operations,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
