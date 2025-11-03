# SCIMListResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Schemas** | Pointer to **[]string** |  | [optional] [default to [urn:ietf:params:scim:api:messages:2.0:ListResponse]]
**TotalResults** | **int32** |  |
**StartIndex** | Pointer to **int32** |  | [optional] [default to 1]
**ItemsPerPage** | **int32** |  |
**Resources** | **[]interface{}** |  |

## Methods

### NewSCIMListResponse

`func NewSCIMListResponse(totalResults int32, itemsPerPage int32, resources []interface{}, ) *SCIMListResponse`

NewSCIMListResponse instantiates a new SCIMListResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMListResponseWithDefaults

`func NewSCIMListResponseWithDefaults() *SCIMListResponse`

NewSCIMListResponseWithDefaults instantiates a new SCIMListResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetSchemas

`func (o *SCIMListResponse) GetSchemas() []string`

GetSchemas returns the Schemas field if non-nil, zero value otherwise.

### GetSchemasOk

`func (o *SCIMListResponse) GetSchemasOk() (*[]string, bool)`

GetSchemasOk returns a tuple with the Schemas field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSchemas

`func (o *SCIMListResponse) SetSchemas(v []string)`

SetSchemas sets Schemas field to given value.

### HasSchemas

`func (o *SCIMListResponse) HasSchemas() bool`

HasSchemas returns a boolean if a field has been set.

### GetTotalResults

`func (o *SCIMListResponse) GetTotalResults() int32`

GetTotalResults returns the TotalResults field if non-nil, zero value otherwise.

### GetTotalResultsOk

`func (o *SCIMListResponse) GetTotalResultsOk() (*int32, bool)`

GetTotalResultsOk returns a tuple with the TotalResults field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalResults

`func (o *SCIMListResponse) SetTotalResults(v int32)`

SetTotalResults sets TotalResults field to given value.


### GetStartIndex

`func (o *SCIMListResponse) GetStartIndex() int32`

GetStartIndex returns the StartIndex field if non-nil, zero value otherwise.

### GetStartIndexOk

`func (o *SCIMListResponse) GetStartIndexOk() (*int32, bool)`

GetStartIndexOk returns a tuple with the StartIndex field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStartIndex

`func (o *SCIMListResponse) SetStartIndex(v int32)`

SetStartIndex sets StartIndex field to given value.

### HasStartIndex

`func (o *SCIMListResponse) HasStartIndex() bool`

HasStartIndex returns a boolean if a field has been set.

### GetItemsPerPage

`func (o *SCIMListResponse) GetItemsPerPage() int32`

GetItemsPerPage returns the ItemsPerPage field if non-nil, zero value otherwise.

### GetItemsPerPageOk

`func (o *SCIMListResponse) GetItemsPerPageOk() (*int32, bool)`

GetItemsPerPageOk returns a tuple with the ItemsPerPage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetItemsPerPage

`func (o *SCIMListResponse) SetItemsPerPage(v int32)`

SetItemsPerPage sets ItemsPerPage field to given value.


### GetResources

`func (o *SCIMListResponse) GetResources() []interface{}`

GetResources returns the Resources field if non-nil, zero value otherwise.

### GetResourcesOk

`func (o *SCIMListResponse) GetResourcesOk() (*[]interface{}, bool)`

GetResourcesOk returns a tuple with the Resources field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetResources

`func (o *SCIMListResponse) SetResources(v []interface{})`

SetResources sets Resources field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
