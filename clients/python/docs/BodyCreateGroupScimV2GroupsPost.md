# BodyCreateGroupScimV2GroupsPost


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**group_data** | **Dict[str, object]** |  | 
**credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Example

```python
from mcp_client.models.body_create_group_scim_v2_groups_post import BodyCreateGroupScimV2GroupsPost

# TODO update the JSON string below
json = "{}"
# create an instance of BodyCreateGroupScimV2GroupsPost from a JSON string
body_create_group_scim_v2_groups_post_instance = BodyCreateGroupScimV2GroupsPost.from_json(json)
# print the JSON string representation of the object
print(BodyCreateGroupScimV2GroupsPost.to_json())

# convert the object into a dict
body_create_group_scim_v2_groups_post_dict = body_create_group_scim_v2_groups_post_instance.to_dict()
# create an instance of BodyCreateGroupScimV2GroupsPost from a dict
body_create_group_scim_v2_groups_post_from_dict = BodyCreateGroupScimV2GroupsPost.from_dict(body_create_group_scim_v2_groups_post_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


