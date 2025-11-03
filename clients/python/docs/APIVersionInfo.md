# APIVersionInfo

API version metadata  Follows semantic versioning (MAJOR.MINOR.PATCH): - MAJOR: Breaking changes (incompatible API changes) - MINOR: New features (backward-compatible) - PATCH: Bug fixes (backward-compatible)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **str** | Application version (semantic versioning: MAJOR.MINOR.PATCH) | 
**api_version** | **str** | Current API version (e.g., &#39;v1&#39;) | 
**supported_versions** | **List[str]** | List of supported API versions | 
**deprecated_versions** | **List[str]** | List of deprecated API versions (still functional but will be removed) | [optional] 
**sunset_dates** | **Dict[str, str]** | Sunset dates for deprecated versions (ISO 8601 format) | [optional] 
**changelog_url** | **str** |  | [optional] 
**documentation_url** | **str** |  | [optional] 

## Example

```python
from mcp_client.models.api_version_info import APIVersionInfo

# TODO update the JSON string below
json = "{}"
# create an instance of APIVersionInfo from a JSON string
api_version_info_instance = APIVersionInfo.from_json(json)
# print the JSON string representation of the object
print(APIVersionInfo.to_json())

# convert the object into a dict
api_version_info_dict = api_version_info_instance.to_dict()
# create an instance of APIVersionInfo from a dict
api_version_info_from_dict = APIVersionInfo.from_dict(api_version_info_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


