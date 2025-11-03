# ConsentRecord

Consent record for GDPR Article 21

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**consent_type** | [**ConsentType**](ConsentType.md) | Type of consent | 
**granted** | **bool** | Whether consent is granted | 
**timestamp** | **str** |  | [optional] 
**ip_address** | **str** |  | [optional] 
**user_agent** | **str** |  | [optional] 

## Example

```python
from mcp_client.models.consent_record import ConsentRecord

# TODO update the JSON string below
json = "{}"
# create an instance of ConsentRecord from a JSON string
consent_record_instance = ConsentRecord.from_json(json)
# print the JSON string representation of the object
print(ConsentRecord.to_json())

# convert the object into a dict
consent_record_dict = consent_record_instance.to_dict()
# create an instance of ConsentRecord from a dict
consent_record_from_dict = ConsentRecord.from_dict(consent_record_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


