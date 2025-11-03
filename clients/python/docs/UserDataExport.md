# UserDataExport

Complete user data export for GDPR compliance  Includes all personal data associated with a user.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**export_id** | **str** | Unique export identifier | 
**export_timestamp** | **str** | ISO timestamp of export | 
**user_id** | **str** | User identifier | 
**username** | **str** | Username | 
**email** | **str** | User email address | 
**profile** | **Dict[str, object]** | User profile data | [optional] 
**sessions** | **List[Optional[Dict[str, object]]]** | Active and recent sessions | [optional] 
**conversations** | **List[Optional[Dict[str, object]]]** | Conversation history | [optional] 
**preferences** | **Dict[str, object]** | User preferences and settings | [optional] 
**audit_log** | **List[Optional[Dict[str, object]]]** | User activity audit log | [optional] 
**consents** | **List[Optional[Dict[str, object]]]** | Consent records | [optional] 
**metadata** | **Dict[str, object]** | Additional metadata | [optional] 

## Example

```python
from mcp_client.models.user_data_export import UserDataExport

# TODO update the JSON string below
json = "{}"
# create an instance of UserDataExport from a JSON string
user_data_export_instance = UserDataExport.from_json(json)
# print the JSON string representation of the object
print(UserDataExport.to_json())

# convert the object into a dict
user_data_export_dict = user_data_export_instance.to_dict()
# create an instance of UserDataExport from a dict
user_data_export_from_dict = UserDataExport.from_dict(user_data_export_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


