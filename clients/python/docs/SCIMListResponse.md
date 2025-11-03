# SCIMListResponse

SCIM List Response

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemas** | **List[str]** |  | [optional] [default to [urn:ietf:params:scim:api:messages:2.0:ListResponse]]
**total_results** | **int** |  |
**start_index** | **int** |  | [optional] [default to 1]
**items_per_page** | **int** |  |
**resources** | **List[object]** |  |

## Example

```python
from mcp_client.models.scim_list_response import SCIMListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMListResponse from a JSON string
scim_list_response_instance = SCIMListResponse.from_json(json)
# print the JSON string representation of the object
print(SCIMListResponse.to_json())

# convert the object into a dict
scim_list_response_dict = scim_list_response_instance.to_dict()
# create an instance of SCIMListResponse from a dict
scim_list_response_from_dict = SCIMListResponse.from_dict(scim_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
