# RotateAPIKeyResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**KeyId** | **string** |  |
**NewApiKey** | **string** | New API key |
**Message** | Pointer to **string** |  | [optional] [default to "API key rotated successfully. Update your client configuration."]

## Methods

### NewRotateAPIKeyResponse

`func NewRotateAPIKeyResponse(keyId string, newApiKey string, ) *RotateAPIKeyResponse`

NewRotateAPIKeyResponse instantiates a new RotateAPIKeyResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRotateAPIKeyResponseWithDefaults

`func NewRotateAPIKeyResponseWithDefaults() *RotateAPIKeyResponse`

NewRotateAPIKeyResponseWithDefaults instantiates a new RotateAPIKeyResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetKeyId

`func (o *RotateAPIKeyResponse) GetKeyId() string`

GetKeyId returns the KeyId field if non-nil, zero value otherwise.

### GetKeyIdOk

`func (o *RotateAPIKeyResponse) GetKeyIdOk() (*string, bool)`

GetKeyIdOk returns a tuple with the KeyId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetKeyId

`func (o *RotateAPIKeyResponse) SetKeyId(v string)`

SetKeyId sets KeyId field to given value.


### GetNewApiKey

`func (o *RotateAPIKeyResponse) GetNewApiKey() string`

GetNewApiKey returns the NewApiKey field if non-nil, zero value otherwise.

### GetNewApiKeyOk

`func (o *RotateAPIKeyResponse) GetNewApiKeyOk() (*string, bool)`

GetNewApiKeyOk returns a tuple with the NewApiKey field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNewApiKey

`func (o *RotateAPIKeyResponse) SetNewApiKey(v string)`

SetNewApiKey sets NewApiKey field to given value.


### GetMessage

`func (o *RotateAPIKeyResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *RotateAPIKeyResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *RotateAPIKeyResponse) SetMessage(v string)`

SetMessage sets Message field to given value.

### HasMessage

`func (o *RotateAPIKeyResponse) HasMessage() bool`

HasMessage returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
