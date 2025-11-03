# SCIMEmail

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Value** | **string** |  | 
**Type** | Pointer to **NullableString** |  | [optional] 
**Primary** | Pointer to **bool** |  | [optional] [default to false]

## Methods

### NewSCIMEmail

`func NewSCIMEmail(value string, ) *SCIMEmail`

NewSCIMEmail instantiates a new SCIMEmail object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMEmailWithDefaults

`func NewSCIMEmailWithDefaults() *SCIMEmail`

NewSCIMEmailWithDefaults instantiates a new SCIMEmail object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetValue

`func (o *SCIMEmail) GetValue() string`

GetValue returns the Value field if non-nil, zero value otherwise.

### GetValueOk

`func (o *SCIMEmail) GetValueOk() (*string, bool)`

GetValueOk returns a tuple with the Value field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetValue

`func (o *SCIMEmail) SetValue(v string)`

SetValue sets Value field to given value.


### GetType

`func (o *SCIMEmail) GetType() string`

GetType returns the Type field if non-nil, zero value otherwise.

### GetTypeOk

`func (o *SCIMEmail) GetTypeOk() (*string, bool)`

GetTypeOk returns a tuple with the Type field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetType

`func (o *SCIMEmail) SetType(v string)`

SetType sets Type field to given value.

### HasType

`func (o *SCIMEmail) HasType() bool`

HasType returns a boolean if a field has been set.

### SetTypeNil

`func (o *SCIMEmail) SetTypeNil(b bool)`

 SetTypeNil sets the value for Type to be an explicit nil

### UnsetType
`func (o *SCIMEmail) UnsetType()`

UnsetType ensures that no value is present for Type, not even an explicit nil
### GetPrimary

`func (o *SCIMEmail) GetPrimary() bool`

GetPrimary returns the Primary field if non-nil, zero value otherwise.

### GetPrimaryOk

`func (o *SCIMEmail) GetPrimaryOk() (*bool, bool)`

GetPrimaryOk returns a tuple with the Primary field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrimary

`func (o *SCIMEmail) SetPrimary(v bool)`

SetPrimary sets Primary field to given value.

### HasPrimary

`func (o *SCIMEmail) HasPrimary() bool`

HasPrimary returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


