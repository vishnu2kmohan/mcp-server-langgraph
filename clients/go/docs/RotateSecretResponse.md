# RotateSecretResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ServiceId** | **string** |  | 
**ClientSecret** | **string** | New client secret | 
**Message** | Pointer to **string** |  | [optional] [default to "Secret rotated successfully. Update your service configuration."]

## Methods

### NewRotateSecretResponse

`func NewRotateSecretResponse(serviceId string, clientSecret string, ) *RotateSecretResponse`

NewRotateSecretResponse instantiates a new RotateSecretResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRotateSecretResponseWithDefaults

`func NewRotateSecretResponseWithDefaults() *RotateSecretResponse`

NewRotateSecretResponseWithDefaults instantiates a new RotateSecretResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetServiceId

`func (o *RotateSecretResponse) GetServiceId() string`

GetServiceId returns the ServiceId field if non-nil, zero value otherwise.

### GetServiceIdOk

`func (o *RotateSecretResponse) GetServiceIdOk() (*string, bool)`

GetServiceIdOk returns a tuple with the ServiceId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetServiceId

`func (o *RotateSecretResponse) SetServiceId(v string)`

SetServiceId sets ServiceId field to given value.


### GetClientSecret

`func (o *RotateSecretResponse) GetClientSecret() string`

GetClientSecret returns the ClientSecret field if non-nil, zero value otherwise.

### GetClientSecretOk

`func (o *RotateSecretResponse) GetClientSecretOk() (*string, bool)`

GetClientSecretOk returns a tuple with the ClientSecret field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetClientSecret

`func (o *RotateSecretResponse) SetClientSecret(v string)`

SetClientSecret sets ClientSecret field to given value.


### GetMessage

`func (o *RotateSecretResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *RotateSecretResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *RotateSecretResponse) SetMessage(v string)`

SetMessage sets Message field to given value.

### HasMessage

`func (o *RotateSecretResponse) HasMessage() bool`

HasMessage returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


