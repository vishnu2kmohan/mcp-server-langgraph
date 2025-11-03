# SCIMPatchRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Schemas** | Pointer to **[]string** |  | [optional] [default to [urn:ietf:params:scim:api:messages:2.0:PatchOp]]
**Operations** | [**[]SCIMPatchOperation**](SCIMPatchOperation.md) |  | 

## Methods

### NewSCIMPatchRequest

`func NewSCIMPatchRequest(operations []SCIMPatchOperation, ) *SCIMPatchRequest`

NewSCIMPatchRequest instantiates a new SCIMPatchRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMPatchRequestWithDefaults

`func NewSCIMPatchRequestWithDefaults() *SCIMPatchRequest`

NewSCIMPatchRequestWithDefaults instantiates a new SCIMPatchRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetSchemas

`func (o *SCIMPatchRequest) GetSchemas() []string`

GetSchemas returns the Schemas field if non-nil, zero value otherwise.

### GetSchemasOk

`func (o *SCIMPatchRequest) GetSchemasOk() (*[]string, bool)`

GetSchemasOk returns a tuple with the Schemas field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSchemas

`func (o *SCIMPatchRequest) SetSchemas(v []string)`

SetSchemas sets Schemas field to given value.

### HasSchemas

`func (o *SCIMPatchRequest) HasSchemas() bool`

HasSchemas returns a boolean if a field has been set.

### GetOperations

`func (o *SCIMPatchRequest) GetOperations() []SCIMPatchOperation`

GetOperations returns the Operations field if non-nil, zero value otherwise.

### GetOperationsOk

`func (o *SCIMPatchRequest) GetOperationsOk() (*[]SCIMPatchOperation, bool)`

GetOperationsOk returns a tuple with the Operations field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOperations

`func (o *SCIMPatchRequest) SetOperations(v []SCIMPatchOperation)`

SetOperations sets Operations field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


