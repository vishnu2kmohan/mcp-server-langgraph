# SCIMPhoneNumber

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Value** | **string** |  | 
**Type** | Pointer to **NullableString** |  | [optional] 
**Primary** | Pointer to **bool** |  | [optional] [default to false]

## Methods

### NewSCIMPhoneNumber

`func NewSCIMPhoneNumber(value string, ) *SCIMPhoneNumber`

NewSCIMPhoneNumber instantiates a new SCIMPhoneNumber object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMPhoneNumberWithDefaults

`func NewSCIMPhoneNumberWithDefaults() *SCIMPhoneNumber`

NewSCIMPhoneNumberWithDefaults instantiates a new SCIMPhoneNumber object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetValue

`func (o *SCIMPhoneNumber) GetValue() string`

GetValue returns the Value field if non-nil, zero value otherwise.

### GetValueOk

`func (o *SCIMPhoneNumber) GetValueOk() (*string, bool)`

GetValueOk returns a tuple with the Value field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetValue

`func (o *SCIMPhoneNumber) SetValue(v string)`

SetValue sets Value field to given value.


### GetType

`func (o *SCIMPhoneNumber) GetType() string`

GetType returns the Type field if non-nil, zero value otherwise.

### GetTypeOk

`func (o *SCIMPhoneNumber) GetTypeOk() (*string, bool)`

GetTypeOk returns a tuple with the Type field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetType

`func (o *SCIMPhoneNumber) SetType(v string)`

SetType sets Type field to given value.

### HasType

`func (o *SCIMPhoneNumber) HasType() bool`

HasType returns a boolean if a field has been set.

### SetTypeNil

`func (o *SCIMPhoneNumber) SetTypeNil(b bool)`

 SetTypeNil sets the value for Type to be an explicit nil

### UnsetType
`func (o *SCIMPhoneNumber) UnsetType()`

UnsetType ensures that no value is present for Type, not even an explicit nil
### GetPrimary

`func (o *SCIMPhoneNumber) GetPrimary() bool`

GetPrimary returns the Primary field if non-nil, zero value otherwise.

### GetPrimaryOk

`func (o *SCIMPhoneNumber) GetPrimaryOk() (*bool, bool)`

GetPrimaryOk returns a tuple with the Primary field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrimary

`func (o *SCIMPhoneNumber) SetPrimary(v bool)`

SetPrimary sets Primary field to given value.

### HasPrimary

`func (o *SCIMPhoneNumber) HasPrimary() bool`

HasPrimary returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


