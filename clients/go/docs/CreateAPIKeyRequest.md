# CreateAPIKeyRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** | Human-readable name for the API key | 
**ExpiresDays** | Pointer to **int32** | Days until expiration (default: 365) | [optional] [default to 365]

## Methods

### NewCreateAPIKeyRequest

`func NewCreateAPIKeyRequest(name string, ) *CreateAPIKeyRequest`

NewCreateAPIKeyRequest instantiates a new CreateAPIKeyRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCreateAPIKeyRequestWithDefaults

`func NewCreateAPIKeyRequestWithDefaults() *CreateAPIKeyRequest`

NewCreateAPIKeyRequestWithDefaults instantiates a new CreateAPIKeyRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *CreateAPIKeyRequest) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *CreateAPIKeyRequest) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *CreateAPIKeyRequest) SetName(v string)`

SetName sets Name field to given value.


### GetExpiresDays

`func (o *CreateAPIKeyRequest) GetExpiresDays() int32`

GetExpiresDays returns the ExpiresDays field if non-nil, zero value otherwise.

### GetExpiresDaysOk

`func (o *CreateAPIKeyRequest) GetExpiresDaysOk() (*int32, bool)`

GetExpiresDaysOk returns a tuple with the ExpiresDays field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExpiresDays

`func (o *CreateAPIKeyRequest) SetExpiresDays(v int32)`

SetExpiresDays sets ExpiresDays field to given value.

### HasExpiresDays

`func (o *CreateAPIKeyRequest) HasExpiresDays() bool`

HasExpiresDays returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


