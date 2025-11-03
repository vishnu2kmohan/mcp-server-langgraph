# SCIMAddress

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Formatted** | Pointer to **NullableString** |  | [optional]
**StreetAddress** | Pointer to **NullableString** |  | [optional]
**Locality** | Pointer to **NullableString** |  | [optional]
**Region** | Pointer to **NullableString** |  | [optional]
**PostalCode** | Pointer to **NullableString** |  | [optional]
**Country** | Pointer to **NullableString** |  | [optional]
**Type** | Pointer to **NullableString** |  | [optional]
**Primary** | Pointer to **bool** |  | [optional] [default to false]

## Methods

### NewSCIMAddress

`func NewSCIMAddress() *SCIMAddress`

NewSCIMAddress instantiates a new SCIMAddress object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMAddressWithDefaults

`func NewSCIMAddressWithDefaults() *SCIMAddress`

NewSCIMAddressWithDefaults instantiates a new SCIMAddress object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetFormatted

`func (o *SCIMAddress) GetFormatted() string`

GetFormatted returns the Formatted field if non-nil, zero value otherwise.

### GetFormattedOk

`func (o *SCIMAddress) GetFormattedOk() (*string, bool)`

GetFormattedOk returns a tuple with the Formatted field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFormatted

`func (o *SCIMAddress) SetFormatted(v string)`

SetFormatted sets Formatted field to given value.

### HasFormatted

`func (o *SCIMAddress) HasFormatted() bool`

HasFormatted returns a boolean if a field has been set.

### SetFormattedNil

`func (o *SCIMAddress) SetFormattedNil(b bool)`

 SetFormattedNil sets the value for Formatted to be an explicit nil

### UnsetFormatted
`func (o *SCIMAddress) UnsetFormatted()`

UnsetFormatted ensures that no value is present for Formatted, not even an explicit nil
### GetStreetAddress

`func (o *SCIMAddress) GetStreetAddress() string`

GetStreetAddress returns the StreetAddress field if non-nil, zero value otherwise.

### GetStreetAddressOk

`func (o *SCIMAddress) GetStreetAddressOk() (*string, bool)`

GetStreetAddressOk returns a tuple with the StreetAddress field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStreetAddress

`func (o *SCIMAddress) SetStreetAddress(v string)`

SetStreetAddress sets StreetAddress field to given value.

### HasStreetAddress

`func (o *SCIMAddress) HasStreetAddress() bool`

HasStreetAddress returns a boolean if a field has been set.

### SetStreetAddressNil

`func (o *SCIMAddress) SetStreetAddressNil(b bool)`

 SetStreetAddressNil sets the value for StreetAddress to be an explicit nil

### UnsetStreetAddress
`func (o *SCIMAddress) UnsetStreetAddress()`

UnsetStreetAddress ensures that no value is present for StreetAddress, not even an explicit nil
### GetLocality

`func (o *SCIMAddress) GetLocality() string`

GetLocality returns the Locality field if non-nil, zero value otherwise.

### GetLocalityOk

`func (o *SCIMAddress) GetLocalityOk() (*string, bool)`

GetLocalityOk returns a tuple with the Locality field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLocality

`func (o *SCIMAddress) SetLocality(v string)`

SetLocality sets Locality field to given value.

### HasLocality

`func (o *SCIMAddress) HasLocality() bool`

HasLocality returns a boolean if a field has been set.

### SetLocalityNil

`func (o *SCIMAddress) SetLocalityNil(b bool)`

 SetLocalityNil sets the value for Locality to be an explicit nil

### UnsetLocality
`func (o *SCIMAddress) UnsetLocality()`

UnsetLocality ensures that no value is present for Locality, not even an explicit nil
### GetRegion

`func (o *SCIMAddress) GetRegion() string`

GetRegion returns the Region field if non-nil, zero value otherwise.

### GetRegionOk

`func (o *SCIMAddress) GetRegionOk() (*string, bool)`

GetRegionOk returns a tuple with the Region field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRegion

`func (o *SCIMAddress) SetRegion(v string)`

SetRegion sets Region field to given value.

### HasRegion

`func (o *SCIMAddress) HasRegion() bool`

HasRegion returns a boolean if a field has been set.

### SetRegionNil

`func (o *SCIMAddress) SetRegionNil(b bool)`

 SetRegionNil sets the value for Region to be an explicit nil

### UnsetRegion
`func (o *SCIMAddress) UnsetRegion()`

UnsetRegion ensures that no value is present for Region, not even an explicit nil
### GetPostalCode

`func (o *SCIMAddress) GetPostalCode() string`

GetPostalCode returns the PostalCode field if non-nil, zero value otherwise.

### GetPostalCodeOk

`func (o *SCIMAddress) GetPostalCodeOk() (*string, bool)`

GetPostalCodeOk returns a tuple with the PostalCode field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPostalCode

`func (o *SCIMAddress) SetPostalCode(v string)`

SetPostalCode sets PostalCode field to given value.

### HasPostalCode

`func (o *SCIMAddress) HasPostalCode() bool`

HasPostalCode returns a boolean if a field has been set.

### SetPostalCodeNil

`func (o *SCIMAddress) SetPostalCodeNil(b bool)`

 SetPostalCodeNil sets the value for PostalCode to be an explicit nil

### UnsetPostalCode
`func (o *SCIMAddress) UnsetPostalCode()`

UnsetPostalCode ensures that no value is present for PostalCode, not even an explicit nil
### GetCountry

`func (o *SCIMAddress) GetCountry() string`

GetCountry returns the Country field if non-nil, zero value otherwise.

### GetCountryOk

`func (o *SCIMAddress) GetCountryOk() (*string, bool)`

GetCountryOk returns a tuple with the Country field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCountry

`func (o *SCIMAddress) SetCountry(v string)`

SetCountry sets Country field to given value.

### HasCountry

`func (o *SCIMAddress) HasCountry() bool`

HasCountry returns a boolean if a field has been set.

### SetCountryNil

`func (o *SCIMAddress) SetCountryNil(b bool)`

 SetCountryNil sets the value for Country to be an explicit nil

### UnsetCountry
`func (o *SCIMAddress) UnsetCountry()`

UnsetCountry ensures that no value is present for Country, not even an explicit nil
### GetType

`func (o *SCIMAddress) GetType() string`

GetType returns the Type field if non-nil, zero value otherwise.

### GetTypeOk

`func (o *SCIMAddress) GetTypeOk() (*string, bool)`

GetTypeOk returns a tuple with the Type field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetType

`func (o *SCIMAddress) SetType(v string)`

SetType sets Type field to given value.

### HasType

`func (o *SCIMAddress) HasType() bool`

HasType returns a boolean if a field has been set.

### SetTypeNil

`func (o *SCIMAddress) SetTypeNil(b bool)`

 SetTypeNil sets the value for Type to be an explicit nil

### UnsetType
`func (o *SCIMAddress) UnsetType()`

UnsetType ensures that no value is present for Type, not even an explicit nil
### GetPrimary

`func (o *SCIMAddress) GetPrimary() bool`

GetPrimary returns the Primary field if non-nil, zero value otherwise.

### GetPrimaryOk

`func (o *SCIMAddress) GetPrimaryOk() (*bool, bool)`

GetPrimaryOk returns a tuple with the Primary field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrimary

`func (o *SCIMAddress) SetPrimary(v bool)`

SetPrimary sets Primary field to given value.

### HasPrimary

`func (o *SCIMAddress) HasPrimary() bool`

HasPrimary returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
