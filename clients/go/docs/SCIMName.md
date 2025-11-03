# SCIMName

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Formatted** | Pointer to **NullableString** |  | [optional] 
**FamilyName** | Pointer to **NullableString** |  | [optional] 
**GivenName** | Pointer to **NullableString** |  | [optional] 
**MiddleName** | Pointer to **NullableString** |  | [optional] 
**HonorificPrefix** | Pointer to **NullableString** |  | [optional] 
**HonorificSuffix** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewSCIMName

`func NewSCIMName() *SCIMName`

NewSCIMName instantiates a new SCIMName object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMNameWithDefaults

`func NewSCIMNameWithDefaults() *SCIMName`

NewSCIMNameWithDefaults instantiates a new SCIMName object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetFormatted

`func (o *SCIMName) GetFormatted() string`

GetFormatted returns the Formatted field if non-nil, zero value otherwise.

### GetFormattedOk

`func (o *SCIMName) GetFormattedOk() (*string, bool)`

GetFormattedOk returns a tuple with the Formatted field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFormatted

`func (o *SCIMName) SetFormatted(v string)`

SetFormatted sets Formatted field to given value.

### HasFormatted

`func (o *SCIMName) HasFormatted() bool`

HasFormatted returns a boolean if a field has been set.

### SetFormattedNil

`func (o *SCIMName) SetFormattedNil(b bool)`

 SetFormattedNil sets the value for Formatted to be an explicit nil

### UnsetFormatted
`func (o *SCIMName) UnsetFormatted()`

UnsetFormatted ensures that no value is present for Formatted, not even an explicit nil
### GetFamilyName

`func (o *SCIMName) GetFamilyName() string`

GetFamilyName returns the FamilyName field if non-nil, zero value otherwise.

### GetFamilyNameOk

`func (o *SCIMName) GetFamilyNameOk() (*string, bool)`

GetFamilyNameOk returns a tuple with the FamilyName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFamilyName

`func (o *SCIMName) SetFamilyName(v string)`

SetFamilyName sets FamilyName field to given value.

### HasFamilyName

`func (o *SCIMName) HasFamilyName() bool`

HasFamilyName returns a boolean if a field has been set.

### SetFamilyNameNil

`func (o *SCIMName) SetFamilyNameNil(b bool)`

 SetFamilyNameNil sets the value for FamilyName to be an explicit nil

### UnsetFamilyName
`func (o *SCIMName) UnsetFamilyName()`

UnsetFamilyName ensures that no value is present for FamilyName, not even an explicit nil
### GetGivenName

`func (o *SCIMName) GetGivenName() string`

GetGivenName returns the GivenName field if non-nil, zero value otherwise.

### GetGivenNameOk

`func (o *SCIMName) GetGivenNameOk() (*string, bool)`

GetGivenNameOk returns a tuple with the GivenName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGivenName

`func (o *SCIMName) SetGivenName(v string)`

SetGivenName sets GivenName field to given value.

### HasGivenName

`func (o *SCIMName) HasGivenName() bool`

HasGivenName returns a boolean if a field has been set.

### SetGivenNameNil

`func (o *SCIMName) SetGivenNameNil(b bool)`

 SetGivenNameNil sets the value for GivenName to be an explicit nil

### UnsetGivenName
`func (o *SCIMName) UnsetGivenName()`

UnsetGivenName ensures that no value is present for GivenName, not even an explicit nil
### GetMiddleName

`func (o *SCIMName) GetMiddleName() string`

GetMiddleName returns the MiddleName field if non-nil, zero value otherwise.

### GetMiddleNameOk

`func (o *SCIMName) GetMiddleNameOk() (*string, bool)`

GetMiddleNameOk returns a tuple with the MiddleName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMiddleName

`func (o *SCIMName) SetMiddleName(v string)`

SetMiddleName sets MiddleName field to given value.

### HasMiddleName

`func (o *SCIMName) HasMiddleName() bool`

HasMiddleName returns a boolean if a field has been set.

### SetMiddleNameNil

`func (o *SCIMName) SetMiddleNameNil(b bool)`

 SetMiddleNameNil sets the value for MiddleName to be an explicit nil

### UnsetMiddleName
`func (o *SCIMName) UnsetMiddleName()`

UnsetMiddleName ensures that no value is present for MiddleName, not even an explicit nil
### GetHonorificPrefix

`func (o *SCIMName) GetHonorificPrefix() string`

GetHonorificPrefix returns the HonorificPrefix field if non-nil, zero value otherwise.

### GetHonorificPrefixOk

`func (o *SCIMName) GetHonorificPrefixOk() (*string, bool)`

GetHonorificPrefixOk returns a tuple with the HonorificPrefix field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHonorificPrefix

`func (o *SCIMName) SetHonorificPrefix(v string)`

SetHonorificPrefix sets HonorificPrefix field to given value.

### HasHonorificPrefix

`func (o *SCIMName) HasHonorificPrefix() bool`

HasHonorificPrefix returns a boolean if a field has been set.

### SetHonorificPrefixNil

`func (o *SCIMName) SetHonorificPrefixNil(b bool)`

 SetHonorificPrefixNil sets the value for HonorificPrefix to be an explicit nil

### UnsetHonorificPrefix
`func (o *SCIMName) UnsetHonorificPrefix()`

UnsetHonorificPrefix ensures that no value is present for HonorificPrefix, not even an explicit nil
### GetHonorificSuffix

`func (o *SCIMName) GetHonorificSuffix() string`

GetHonorificSuffix returns the HonorificSuffix field if non-nil, zero value otherwise.

### GetHonorificSuffixOk

`func (o *SCIMName) GetHonorificSuffixOk() (*string, bool)`

GetHonorificSuffixOk returns a tuple with the HonorificSuffix field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHonorificSuffix

`func (o *SCIMName) SetHonorificSuffix(v string)`

SetHonorificSuffix sets HonorificSuffix field to given value.

### HasHonorificSuffix

`func (o *SCIMName) HasHonorificSuffix() bool`

HasHonorificSuffix returns a boolean if a field has been set.

### SetHonorificSuffixNil

`func (o *SCIMName) SetHonorificSuffixNil(b bool)`

 SetHonorificSuffixNil sets the value for HonorificSuffix to be an explicit nil

### UnsetHonorificSuffix
`func (o *SCIMName) UnsetHonorificSuffix()`

UnsetHonorificSuffix ensures that no value is present for HonorificSuffix, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


