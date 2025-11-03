# UserProfileUpdate

User profile update model (GDPR Article 16 - Right to Rectification)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [optional] [default to undefined]
**email** | **string** |  | [optional] [default to undefined]
**preferences** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { UserProfileUpdate } from 'mcp-client';

const instance: UserProfileUpdate = {
    name,
    email,
    preferences,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
