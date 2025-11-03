# UserProfileUpdate

User profile update model (GDPR Article 16 - Right to Rectification)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**email** | **str** |  | [optional] 
**preferences** | **Dict[str, object]** |  | [optional] 

## Example

```python
from mcp_client.models.user_profile_update import UserProfileUpdate

# TODO update the JSON string below
json = "{}"
# create an instance of UserProfileUpdate from a JSON string
user_profile_update_instance = UserProfileUpdate.from_json(json)
# print the JSON string representation of the object
print(UserProfileUpdate.to_json())

# convert the object into a dict
user_profile_update_dict = user_profile_update_instance.to_dict()
# create an instance of UserProfileUpdate from a dict
user_profile_update_from_dict = UserProfileUpdate.from_dict(user_profile_update_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


