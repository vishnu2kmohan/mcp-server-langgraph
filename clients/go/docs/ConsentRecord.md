# ConsentRecord

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ConsentType** | [**ConsentType**](ConsentType.md) | Type of consent |
**Granted** | **bool** | Whether consent is granted |
**Timestamp** | Pointer to **NullableString** |  | [optional]
**IpAddress** | Pointer to **NullableString** |  | [optional]
**UserAgent** | Pointer to **NullableString** |  | [optional]

## Methods

### NewConsentRecord

`func NewConsentRecord(consentType ConsentType, granted bool, ) *ConsentRecord`

NewConsentRecord instantiates a new ConsentRecord object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewConsentRecordWithDefaults

`func NewConsentRecordWithDefaults() *ConsentRecord`

NewConsentRecordWithDefaults instantiates a new ConsentRecord object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetConsentType

`func (o *ConsentRecord) GetConsentType() ConsentType`

GetConsentType returns the ConsentType field if non-nil, zero value otherwise.

### GetConsentTypeOk

`func (o *ConsentRecord) GetConsentTypeOk() (*ConsentType, bool)`

GetConsentTypeOk returns a tuple with the ConsentType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConsentType

`func (o *ConsentRecord) SetConsentType(v ConsentType)`

SetConsentType sets ConsentType field to given value.


### GetGranted

`func (o *ConsentRecord) GetGranted() bool`

GetGranted returns the Granted field if non-nil, zero value otherwise.

### GetGrantedOk

`func (o *ConsentRecord) GetGrantedOk() (*bool, bool)`

GetGrantedOk returns a tuple with the Granted field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGranted

`func (o *ConsentRecord) SetGranted(v bool)`

SetGranted sets Granted field to given value.


### GetTimestamp

`func (o *ConsentRecord) GetTimestamp() string`

GetTimestamp returns the Timestamp field if non-nil, zero value otherwise.

### GetTimestampOk

`func (o *ConsentRecord) GetTimestampOk() (*string, bool)`

GetTimestampOk returns a tuple with the Timestamp field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimestamp

`func (o *ConsentRecord) SetTimestamp(v string)`

SetTimestamp sets Timestamp field to given value.

### HasTimestamp

`func (o *ConsentRecord) HasTimestamp() bool`

HasTimestamp returns a boolean if a field has been set.

### SetTimestampNil

`func (o *ConsentRecord) SetTimestampNil(b bool)`

 SetTimestampNil sets the value for Timestamp to be an explicit nil

### UnsetTimestamp
`func (o *ConsentRecord) UnsetTimestamp()`

UnsetTimestamp ensures that no value is present for Timestamp, not even an explicit nil
### GetIpAddress

`func (o *ConsentRecord) GetIpAddress() string`

GetIpAddress returns the IpAddress field if non-nil, zero value otherwise.

### GetIpAddressOk

`func (o *ConsentRecord) GetIpAddressOk() (*string, bool)`

GetIpAddressOk returns a tuple with the IpAddress field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIpAddress

`func (o *ConsentRecord) SetIpAddress(v string)`

SetIpAddress sets IpAddress field to given value.

### HasIpAddress

`func (o *ConsentRecord) HasIpAddress() bool`

HasIpAddress returns a boolean if a field has been set.

### SetIpAddressNil

`func (o *ConsentRecord) SetIpAddressNil(b bool)`

 SetIpAddressNil sets the value for IpAddress to be an explicit nil

### UnsetIpAddress
`func (o *ConsentRecord) UnsetIpAddress()`

UnsetIpAddress ensures that no value is present for IpAddress, not even an explicit nil
### GetUserAgent

`func (o *ConsentRecord) GetUserAgent() string`

GetUserAgent returns the UserAgent field if non-nil, zero value otherwise.

### GetUserAgentOk

`func (o *ConsentRecord) GetUserAgentOk() (*string, bool)`

GetUserAgentOk returns a tuple with the UserAgent field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUserAgent

`func (o *ConsentRecord) SetUserAgent(v string)`

SetUserAgent sets UserAgent field to given value.

### HasUserAgent

`func (o *ConsentRecord) HasUserAgent() bool`

HasUserAgent returns a boolean if a field has been set.

### SetUserAgentNil

`func (o *ConsentRecord) SetUserAgentNil(b bool)`

 SetUserAgentNil sets the value for UserAgent to be an explicit nil

### UnsetUserAgent
`func (o *ConsentRecord) UnsetUserAgent()`

UnsetUserAgent ensures that no value is present for UserAgent, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
