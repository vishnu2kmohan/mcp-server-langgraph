# BodyUpdateUserProfileApiV1UsersMePatch


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**profile_update** | [**UserProfileUpdate**](UserProfileUpdate.md) |  | 
**credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Example

```python
from mcp_client.models.body_update_user_profile_api_v1_users_me_patch import BodyUpdateUserProfileApiV1UsersMePatch

# TODO update the JSON string below
json = "{}"
# create an instance of BodyUpdateUserProfileApiV1UsersMePatch from a JSON string
body_update_user_profile_api_v1_users_me_patch_instance = BodyUpdateUserProfileApiV1UsersMePatch.from_json(json)
# print the JSON string representation of the object
print(BodyUpdateUserProfileApiV1UsersMePatch.to_json())

# convert the object into a dict
body_update_user_profile_api_v1_users_me_patch_dict = body_update_user_profile_api_v1_users_me_patch_instance.to_dict()
# create an instance of BodyUpdateUserProfileApiV1UsersMePatch from a dict
body_update_user_profile_api_v1_users_me_patch_from_dict = BodyUpdateUserProfileApiV1UsersMePatch.from_dict(body_update_user_profile_api_v1_users_me_patch_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


