# SCIMUser

SCIM 2.0 User Resource  Core schema with optional Enterprise extension.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemas** | **Array&lt;string | null&gt;** |  | [optional] [default to undefined]
**id** | **string** |  | [optional] [default to undefined]
**externalId** | **string** |  | [optional] [default to undefined]
**userName** | **string** |  | [default to undefined]
**name** | [**SCIMName**](SCIMName.md) |  | [optional] [default to undefined]
**displayName** | **string** |  | [optional] [default to undefined]
**nickName** | **string** |  | [optional] [default to undefined]
**profileUrl** | **string** |  | [optional] [default to undefined]
**title** | **string** |  | [optional] [default to undefined]
**userType** | **string** |  | [optional] [default to undefined]
**preferredLanguage** | **string** |  | [optional] [default to undefined]
**locale** | **string** |  | [optional] [default to undefined]
**timezone** | **string** |  | [optional] [default to undefined]
**active** | **boolean** |  | [optional] [default to true]
**password** | **string** |  | [optional] [default to undefined]
**emails** | [**Array&lt;SCIMEmail&gt;**](SCIMEmail.md) |  | [optional] [default to undefined]
**phoneNumbers** | [**Array&lt;SCIMPhoneNumber&gt;**](SCIMPhoneNumber.md) |  | [optional] [default to undefined]
**addresses** | [**Array&lt;SCIMAddress&gt;**](SCIMAddress.md) |  | [optional] [default to undefined]
**groups** | [**Array&lt;SCIMGroupMembership&gt;**](SCIMGroupMembership.md) |  | [optional] [default to undefined]
**meta** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**urn_ietf_params_scim_schemas_extension_enterprise_2_0_User** | [**SCIMEnterpriseUser**](SCIMEnterpriseUser.md) |  | [optional] [default to undefined]

## Example

```typescript
import { SCIMUser } from 'mcp-client';

const instance: SCIMUser = {
    schemas,
    id,
    externalId,
    userName,
    name,
    displayName,
    nickName,
    profileUrl,
    title,
    userType,
    preferredLanguage,
    locale,
    timezone,
    active,
    password,
    emails,
    phoneNumbers,
    addresses,
    groups,
    meta,
    urn_ietf_params_scim_schemas_extension_enterprise_2_0_User,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
