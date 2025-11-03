# BodyCreateUserScimV2UsersPost


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**user_data** | **Dict[str, object]** |  |
**credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional]

## Example

```python
from mcp_client.models.body_create_user_scim_v2_users_post import BodyCreateUserScimV2UsersPost

# TODO update the JSON string below
json = "{}"
# create an instance of BodyCreateUserScimV2UsersPost from a JSON string
body_create_user_scim_v2_users_post_instance = BodyCreateUserScimV2UsersPost.from_json(json)
# print the JSON string representation of the object
print(BodyCreateUserScimV2UsersPost.to_json())

# convert the object into a dict
body_create_user_scim_v2_users_post_dict = body_create_user_scim_v2_users_post_instance.to_dict()
# create an instance of BodyCreateUserScimV2UsersPost from a dict
body_create_user_scim_v2_users_post_from_dict = BodyCreateUserScimV2UsersPost.from_dict(body_create_user_scim_v2_users_post_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
