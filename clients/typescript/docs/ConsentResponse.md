# ConsentResponse

Response for consent operations

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**user_id** | **string** |  | [default to undefined]
**consents** | **{ [key: string]: { [key: string]: any; }; }** | Current consent status for all types | [default to undefined]

## Example

```typescript
import { ConsentResponse } from 'mcp-client';

const instance: ConsentResponse = {
    user_id,
    consents,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
