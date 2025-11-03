# SCIMGroup

SCIM 2.0 Group Resource

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemas** | **Array&lt;string | null&gt;** |  | [optional] [default to undefined]
**id** | **string** |  | [optional] [default to undefined]
**displayName** | **string** |  | [default to undefined]
**members** | [**Array&lt;SCIMMember&gt;**](SCIMMember.md) |  | [optional] [default to undefined]
**meta** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { SCIMGroup } from 'mcp-client';

const instance: SCIMGroup = {
    schemas,
    id,
    displayName,
    members,
    meta,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
