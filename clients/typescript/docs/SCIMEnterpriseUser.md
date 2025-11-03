# SCIMEnterpriseUser

SCIM Enterprise User Extension (RFC 7643 Section 4.3)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**employeeNumber** | **string** |  | [optional] [default to undefined]
**costCenter** | **string** |  | [optional] [default to undefined]
**organization** | **string** |  | [optional] [default to undefined]
**division** | **string** |  | [optional] [default to undefined]
**department** | **string** |  | [optional] [default to undefined]
**manager** | **{ [key: string]: string; }** |  | [optional] [default to undefined]

## Example

```typescript
import { SCIMEnterpriseUser } from 'mcp-client';

const instance: SCIMEnterpriseUser = {
    employeeNumber,
    costCenter,
    organization,
    division,
    department,
    manager,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
