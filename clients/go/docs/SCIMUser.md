# SCIMUser

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Schemas** | Pointer to **[]string** |  | [optional] [default to [urn:ietf:params:scim:schemas:core:2.0:User]]
**Id** | Pointer to **NullableString** |  | [optional]
**ExternalId** | Pointer to **NullableString** |  | [optional]
**UserName** | **string** |  |
**Name** | Pointer to [**NullableSCIMName**](SCIMName.md) |  | [optional]
**DisplayName** | Pointer to **NullableString** |  | [optional]
**NickName** | Pointer to **NullableString** |  | [optional]
**ProfileUrl** | Pointer to **NullableString** |  | [optional]
**Title** | Pointer to **NullableString** |  | [optional]
**UserType** | Pointer to **NullableString** |  | [optional]
**PreferredLanguage** | Pointer to **NullableString** |  | [optional]
**Locale** | Pointer to **NullableString** |  | [optional]
**Timezone** | Pointer to **NullableString** |  | [optional]
**Active** | Pointer to **bool** |  | [optional] [default to true]
**Password** | Pointer to **NullableString** |  | [optional]
**Emails** | Pointer to [**[]SCIMEmail**](SCIMEmail.md) |  | [optional] [default to []]
**PhoneNumbers** | Pointer to [**[]SCIMPhoneNumber**](SCIMPhoneNumber.md) |  | [optional] [default to []]
**Addresses** | Pointer to [**[]SCIMAddress**](SCIMAddress.md) |  | [optional] [default to []]
**Groups** | Pointer to [**[]SCIMGroupMembership**](SCIMGroupMembership.md) |  | [optional] [default to []]
**Meta** | Pointer to **map[string]interface{}** |  | [optional]
**UrnIetfParamsScimSchemasExtensionEnterprise20User** | Pointer to [**NullableSCIMEnterpriseUser**](SCIMEnterpriseUser.md) |  | [optional]

## Methods

### NewSCIMUser

`func NewSCIMUser(userName string, ) *SCIMUser`

NewSCIMUser instantiates a new SCIMUser object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMUserWithDefaults

`func NewSCIMUserWithDefaults() *SCIMUser`

NewSCIMUserWithDefaults instantiates a new SCIMUser object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetSchemas

`func (o *SCIMUser) GetSchemas() []*string`

GetSchemas returns the Schemas field if non-nil, zero value otherwise.

### GetSchemasOk

`func (o *SCIMUser) GetSchemasOk() (*[]*string, bool)`

GetSchemasOk returns a tuple with the Schemas field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSchemas

`func (o *SCIMUser) SetSchemas(v []*string)`

SetSchemas sets Schemas field to given value.

### HasSchemas

`func (o *SCIMUser) HasSchemas() bool`

HasSchemas returns a boolean if a field has been set.

### GetId

`func (o *SCIMUser) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *SCIMUser) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *SCIMUser) SetId(v string)`

SetId sets Id field to given value.

### HasId

`func (o *SCIMUser) HasId() bool`

HasId returns a boolean if a field has been set.

### SetIdNil

`func (o *SCIMUser) SetIdNil(b bool)`

 SetIdNil sets the value for Id to be an explicit nil

### UnsetId
`func (o *SCIMUser) UnsetId()`

UnsetId ensures that no value is present for Id, not even an explicit nil
### GetExternalId

`func (o *SCIMUser) GetExternalId() string`

GetExternalId returns the ExternalId field if non-nil, zero value otherwise.

### GetExternalIdOk

`func (o *SCIMUser) GetExternalIdOk() (*string, bool)`

GetExternalIdOk returns a tuple with the ExternalId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExternalId

`func (o *SCIMUser) SetExternalId(v string)`

SetExternalId sets ExternalId field to given value.

### HasExternalId

`func (o *SCIMUser) HasExternalId() bool`

HasExternalId returns a boolean if a field has been set.

### SetExternalIdNil

`func (o *SCIMUser) SetExternalIdNil(b bool)`

 SetExternalIdNil sets the value for ExternalId to be an explicit nil

### UnsetExternalId
`func (o *SCIMUser) UnsetExternalId()`

UnsetExternalId ensures that no value is present for ExternalId, not even an explicit nil
### GetUserName

`func (o *SCIMUser) GetUserName() string`

GetUserName returns the UserName field if non-nil, zero value otherwise.

### GetUserNameOk

`func (o *SCIMUser) GetUserNameOk() (*string, bool)`

GetUserNameOk returns a tuple with the UserName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUserName

`func (o *SCIMUser) SetUserName(v string)`

SetUserName sets UserName field to given value.


### GetName

`func (o *SCIMUser) GetName() SCIMName`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *SCIMUser) GetNameOk() (*SCIMName, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *SCIMUser) SetName(v SCIMName)`

SetName sets Name field to given value.

### HasName

`func (o *SCIMUser) HasName() bool`

HasName returns a boolean if a field has been set.

### SetNameNil

`func (o *SCIMUser) SetNameNil(b bool)`

 SetNameNil sets the value for Name to be an explicit nil

### UnsetName
`func (o *SCIMUser) UnsetName()`

UnsetName ensures that no value is present for Name, not even an explicit nil
### GetDisplayName

`func (o *SCIMUser) GetDisplayName() string`

GetDisplayName returns the DisplayName field if non-nil, zero value otherwise.

### GetDisplayNameOk

`func (o *SCIMUser) GetDisplayNameOk() (*string, bool)`

GetDisplayNameOk returns a tuple with the DisplayName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDisplayName

`func (o *SCIMUser) SetDisplayName(v string)`

SetDisplayName sets DisplayName field to given value.

### HasDisplayName

`func (o *SCIMUser) HasDisplayName() bool`

HasDisplayName returns a boolean if a field has been set.

### SetDisplayNameNil

`func (o *SCIMUser) SetDisplayNameNil(b bool)`

 SetDisplayNameNil sets the value for DisplayName to be an explicit nil

### UnsetDisplayName
`func (o *SCIMUser) UnsetDisplayName()`

UnsetDisplayName ensures that no value is present for DisplayName, not even an explicit nil
### GetNickName

`func (o *SCIMUser) GetNickName() string`

GetNickName returns the NickName field if non-nil, zero value otherwise.

### GetNickNameOk

`func (o *SCIMUser) GetNickNameOk() (*string, bool)`

GetNickNameOk returns a tuple with the NickName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNickName

`func (o *SCIMUser) SetNickName(v string)`

SetNickName sets NickName field to given value.

### HasNickName

`func (o *SCIMUser) HasNickName() bool`

HasNickName returns a boolean if a field has been set.

### SetNickNameNil

`func (o *SCIMUser) SetNickNameNil(b bool)`

 SetNickNameNil sets the value for NickName to be an explicit nil

### UnsetNickName
`func (o *SCIMUser) UnsetNickName()`

UnsetNickName ensures that no value is present for NickName, not even an explicit nil
### GetProfileUrl

`func (o *SCIMUser) GetProfileUrl() string`

GetProfileUrl returns the ProfileUrl field if non-nil, zero value otherwise.

### GetProfileUrlOk

`func (o *SCIMUser) GetProfileUrlOk() (*string, bool)`

GetProfileUrlOk returns a tuple with the ProfileUrl field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProfileUrl

`func (o *SCIMUser) SetProfileUrl(v string)`

SetProfileUrl sets ProfileUrl field to given value.

### HasProfileUrl

`func (o *SCIMUser) HasProfileUrl() bool`

HasProfileUrl returns a boolean if a field has been set.

### SetProfileUrlNil

`func (o *SCIMUser) SetProfileUrlNil(b bool)`

 SetProfileUrlNil sets the value for ProfileUrl to be an explicit nil

### UnsetProfileUrl
`func (o *SCIMUser) UnsetProfileUrl()`

UnsetProfileUrl ensures that no value is present for ProfileUrl, not even an explicit nil
### GetTitle

`func (o *SCIMUser) GetTitle() string`

GetTitle returns the Title field if non-nil, zero value otherwise.

### GetTitleOk

`func (o *SCIMUser) GetTitleOk() (*string, bool)`

GetTitleOk returns a tuple with the Title field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTitle

`func (o *SCIMUser) SetTitle(v string)`

SetTitle sets Title field to given value.

### HasTitle

`func (o *SCIMUser) HasTitle() bool`

HasTitle returns a boolean if a field has been set.

### SetTitleNil

`func (o *SCIMUser) SetTitleNil(b bool)`

 SetTitleNil sets the value for Title to be an explicit nil

### UnsetTitle
`func (o *SCIMUser) UnsetTitle()`

UnsetTitle ensures that no value is present for Title, not even an explicit nil
### GetUserType

`func (o *SCIMUser) GetUserType() string`

GetUserType returns the UserType field if non-nil, zero value otherwise.

### GetUserTypeOk

`func (o *SCIMUser) GetUserTypeOk() (*string, bool)`

GetUserTypeOk returns a tuple with the UserType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUserType

`func (o *SCIMUser) SetUserType(v string)`

SetUserType sets UserType field to given value.

### HasUserType

`func (o *SCIMUser) HasUserType() bool`

HasUserType returns a boolean if a field has been set.

### SetUserTypeNil

`func (o *SCIMUser) SetUserTypeNil(b bool)`

 SetUserTypeNil sets the value for UserType to be an explicit nil

### UnsetUserType
`func (o *SCIMUser) UnsetUserType()`

UnsetUserType ensures that no value is present for UserType, not even an explicit nil
### GetPreferredLanguage

`func (o *SCIMUser) GetPreferredLanguage() string`

GetPreferredLanguage returns the PreferredLanguage field if non-nil, zero value otherwise.

### GetPreferredLanguageOk

`func (o *SCIMUser) GetPreferredLanguageOk() (*string, bool)`

GetPreferredLanguageOk returns a tuple with the PreferredLanguage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPreferredLanguage

`func (o *SCIMUser) SetPreferredLanguage(v string)`

SetPreferredLanguage sets PreferredLanguage field to given value.

### HasPreferredLanguage

`func (o *SCIMUser) HasPreferredLanguage() bool`

HasPreferredLanguage returns a boolean if a field has been set.

### SetPreferredLanguageNil

`func (o *SCIMUser) SetPreferredLanguageNil(b bool)`

 SetPreferredLanguageNil sets the value for PreferredLanguage to be an explicit nil

### UnsetPreferredLanguage
`func (o *SCIMUser) UnsetPreferredLanguage()`

UnsetPreferredLanguage ensures that no value is present for PreferredLanguage, not even an explicit nil
### GetLocale

`func (o *SCIMUser) GetLocale() string`

GetLocale returns the Locale field if non-nil, zero value otherwise.

### GetLocaleOk

`func (o *SCIMUser) GetLocaleOk() (*string, bool)`

GetLocaleOk returns a tuple with the Locale field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLocale

`func (o *SCIMUser) SetLocale(v string)`

SetLocale sets Locale field to given value.

### HasLocale

`func (o *SCIMUser) HasLocale() bool`

HasLocale returns a boolean if a field has been set.

### SetLocaleNil

`func (o *SCIMUser) SetLocaleNil(b bool)`

 SetLocaleNil sets the value for Locale to be an explicit nil

### UnsetLocale
`func (o *SCIMUser) UnsetLocale()`

UnsetLocale ensures that no value is present for Locale, not even an explicit nil
### GetTimezone

`func (o *SCIMUser) GetTimezone() string`

GetTimezone returns the Timezone field if non-nil, zero value otherwise.

### GetTimezoneOk

`func (o *SCIMUser) GetTimezoneOk() (*string, bool)`

GetTimezoneOk returns a tuple with the Timezone field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimezone

`func (o *SCIMUser) SetTimezone(v string)`

SetTimezone sets Timezone field to given value.

### HasTimezone

`func (o *SCIMUser) HasTimezone() bool`

HasTimezone returns a boolean if a field has been set.

### SetTimezoneNil

`func (o *SCIMUser) SetTimezoneNil(b bool)`

 SetTimezoneNil sets the value for Timezone to be an explicit nil

### UnsetTimezone
`func (o *SCIMUser) UnsetTimezone()`

UnsetTimezone ensures that no value is present for Timezone, not even an explicit nil
### GetActive

`func (o *SCIMUser) GetActive() bool`

GetActive returns the Active field if non-nil, zero value otherwise.

### GetActiveOk

`func (o *SCIMUser) GetActiveOk() (*bool, bool)`

GetActiveOk returns a tuple with the Active field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActive

`func (o *SCIMUser) SetActive(v bool)`

SetActive sets Active field to given value.

### HasActive

`func (o *SCIMUser) HasActive() bool`

HasActive returns a boolean if a field has been set.

### GetPassword

`func (o *SCIMUser) GetPassword() string`

GetPassword returns the Password field if non-nil, zero value otherwise.

### GetPasswordOk

`func (o *SCIMUser) GetPasswordOk() (*string, bool)`

GetPasswordOk returns a tuple with the Password field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPassword

`func (o *SCIMUser) SetPassword(v string)`

SetPassword sets Password field to given value.

### HasPassword

`func (o *SCIMUser) HasPassword() bool`

HasPassword returns a boolean if a field has been set.

### SetPasswordNil

`func (o *SCIMUser) SetPasswordNil(b bool)`

 SetPasswordNil sets the value for Password to be an explicit nil

### UnsetPassword
`func (o *SCIMUser) UnsetPassword()`

UnsetPassword ensures that no value is present for Password, not even an explicit nil
### GetEmails

`func (o *SCIMUser) GetEmails() []SCIMEmail`

GetEmails returns the Emails field if non-nil, zero value otherwise.

### GetEmailsOk

`func (o *SCIMUser) GetEmailsOk() (*[]SCIMEmail, bool)`

GetEmailsOk returns a tuple with the Emails field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEmails

`func (o *SCIMUser) SetEmails(v []SCIMEmail)`

SetEmails sets Emails field to given value.

### HasEmails

`func (o *SCIMUser) HasEmails() bool`

HasEmails returns a boolean if a field has been set.

### GetPhoneNumbers

`func (o *SCIMUser) GetPhoneNumbers() []SCIMPhoneNumber`

GetPhoneNumbers returns the PhoneNumbers field if non-nil, zero value otherwise.

### GetPhoneNumbersOk

`func (o *SCIMUser) GetPhoneNumbersOk() (*[]SCIMPhoneNumber, bool)`

GetPhoneNumbersOk returns a tuple with the PhoneNumbers field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPhoneNumbers

`func (o *SCIMUser) SetPhoneNumbers(v []SCIMPhoneNumber)`

SetPhoneNumbers sets PhoneNumbers field to given value.

### HasPhoneNumbers

`func (o *SCIMUser) HasPhoneNumbers() bool`

HasPhoneNumbers returns a boolean if a field has been set.

### GetAddresses

`func (o *SCIMUser) GetAddresses() []SCIMAddress`

GetAddresses returns the Addresses field if non-nil, zero value otherwise.

### GetAddressesOk

`func (o *SCIMUser) GetAddressesOk() (*[]SCIMAddress, bool)`

GetAddressesOk returns a tuple with the Addresses field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAddresses

`func (o *SCIMUser) SetAddresses(v []SCIMAddress)`

SetAddresses sets Addresses field to given value.

### HasAddresses

`func (o *SCIMUser) HasAddresses() bool`

HasAddresses returns a boolean if a field has been set.

### GetGroups

`func (o *SCIMUser) GetGroups() []SCIMGroupMembership`

GetGroups returns the Groups field if non-nil, zero value otherwise.

### GetGroupsOk

`func (o *SCIMUser) GetGroupsOk() (*[]SCIMGroupMembership, bool)`

GetGroupsOk returns a tuple with the Groups field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGroups

`func (o *SCIMUser) SetGroups(v []SCIMGroupMembership)`

SetGroups sets Groups field to given value.

### HasGroups

`func (o *SCIMUser) HasGroups() bool`

HasGroups returns a boolean if a field has been set.

### GetMeta

`func (o *SCIMUser) GetMeta() map[string]interface{}`

GetMeta returns the Meta field if non-nil, zero value otherwise.

### GetMetaOk

`func (o *SCIMUser) GetMetaOk() (*map[string]interface{}, bool)`

GetMetaOk returns a tuple with the Meta field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMeta

`func (o *SCIMUser) SetMeta(v map[string]interface{})`

SetMeta sets Meta field to given value.

### HasMeta

`func (o *SCIMUser) HasMeta() bool`

HasMeta returns a boolean if a field has been set.

### SetMetaNil

`func (o *SCIMUser) SetMetaNil(b bool)`

 SetMetaNil sets the value for Meta to be an explicit nil

### UnsetMeta
`func (o *SCIMUser) UnsetMeta()`

UnsetMeta ensures that no value is present for Meta, not even an explicit nil
### GetUrnIetfParamsScimSchemasExtensionEnterprise20User

`func (o *SCIMUser) GetUrnIetfParamsScimSchemasExtensionEnterprise20User() SCIMEnterpriseUser`

GetUrnIetfParamsScimSchemasExtensionEnterprise20User returns the UrnIetfParamsScimSchemasExtensionEnterprise20User field if non-nil, zero value otherwise.

### GetUrnIetfParamsScimSchemasExtensionEnterprise20UserOk

`func (o *SCIMUser) GetUrnIetfParamsScimSchemasExtensionEnterprise20UserOk() (*SCIMEnterpriseUser, bool)`

GetUrnIetfParamsScimSchemasExtensionEnterprise20UserOk returns a tuple with the UrnIetfParamsScimSchemasExtensionEnterprise20User field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUrnIetfParamsScimSchemasExtensionEnterprise20User

`func (o *SCIMUser) SetUrnIetfParamsScimSchemasExtensionEnterprise20User(v SCIMEnterpriseUser)`

SetUrnIetfParamsScimSchemasExtensionEnterprise20User sets UrnIetfParamsScimSchemasExtensionEnterprise20User field to given value.

### HasUrnIetfParamsScimSchemasExtensionEnterprise20User

`func (o *SCIMUser) HasUrnIetfParamsScimSchemasExtensionEnterprise20User() bool`

HasUrnIetfParamsScimSchemasExtensionEnterprise20User returns a boolean if a field has been set.

### SetUrnIetfParamsScimSchemasExtensionEnterprise20UserNil

`func (o *SCIMUser) SetUrnIetfParamsScimSchemasExtensionEnterprise20UserNil(b bool)`

 SetUrnIetfParamsScimSchemasExtensionEnterprise20UserNil sets the value for UrnIetfParamsScimSchemasExtensionEnterprise20User to be an explicit nil

### UnsetUrnIetfParamsScimSchemasExtensionEnterprise20User
`func (o *SCIMUser) UnsetUrnIetfParamsScimSchemasExtensionEnterprise20User()`

UnsetUrnIetfParamsScimSchemasExtensionEnterprise20User ensures that no value is present for UrnIetfParamsScimSchemasExtensionEnterprise20User, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
