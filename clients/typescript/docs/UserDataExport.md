# UserDataExport

Complete user data export for GDPR compliance  Includes all personal data associated with a user.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**export_id** | **string** | Unique export identifier | [default to undefined]
**export_timestamp** | **string** | ISO timestamp of export | [default to undefined]
**user_id** | **string** | User identifier | [default to undefined]
**username** | **string** | Username | [default to undefined]
**email** | **string** | User email address | [default to undefined]
**profile** | **{ [key: string]: any; }** | User profile data | [optional] [default to undefined]
**sessions** | **Array&lt;{ [key: string]: any; } | null&gt;** | Active and recent sessions | [optional] [default to undefined]
**conversations** | **Array&lt;{ [key: string]: any; } | null&gt;** | Conversation history | [optional] [default to undefined]
**preferences** | **{ [key: string]: any; }** | User preferences and settings | [optional] [default to undefined]
**audit_log** | **Array&lt;{ [key: string]: any; } | null&gt;** | User activity audit log | [optional] [default to undefined]
**consents** | **Array&lt;{ [key: string]: any; } | null&gt;** | Consent records | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** | Additional metadata | [optional] [default to undefined]

## Example

```typescript
import { UserDataExport } from 'mcp-client';

const instance: UserDataExport = {
    export_id,
    export_timestamp,
    user_id,
    username,
    email,
    profile,
    sessions,
    conversations,
    preferences,
    audit_log,
    consents,
    metadata,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
