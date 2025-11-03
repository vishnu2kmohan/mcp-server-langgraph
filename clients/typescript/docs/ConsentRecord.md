# ConsentRecord

Consent record for GDPR Article 21

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**consent_type** | [**ConsentType**](ConsentType.md) | Type of consent | [default to undefined]
**granted** | **boolean** | Whether consent is granted | [default to undefined]
**timestamp** | **string** |  | [optional] [default to undefined]
**ip_address** | **string** |  | [optional] [default to undefined]
**user_agent** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { ConsentRecord } from 'mcp-client';

const instance: ConsentRecord = {
    consent_type,
    granted,
    timestamp,
    ip_address,
    user_agent,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
