# UserProfileUpdate

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | Pointer to **NullableString** |  | [optional]
**Email** | Pointer to **NullableString** |  | [optional]
**Preferences** | Pointer to **map[string]interface{}** |  | [optional]

## Methods

### NewUserProfileUpdate

`func NewUserProfileUpdate() *UserProfileUpdate`

NewUserProfileUpdate instantiates a new UserProfileUpdate object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewUserProfileUpdateWithDefaults

`func NewUserProfileUpdateWithDefaults() *UserProfileUpdate`

NewUserProfileUpdateWithDefaults instantiates a new UserProfileUpdate object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *UserProfileUpdate) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *UserProfileUpdate) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *UserProfileUpdate) SetName(v string)`

SetName sets Name field to given value.

### HasName

`func (o *UserProfileUpdate) HasName() bool`

HasName returns a boolean if a field has been set.

### SetNameNil

`func (o *UserProfileUpdate) SetNameNil(b bool)`

 SetNameNil sets the value for Name to be an explicit nil

### UnsetName
`func (o *UserProfileUpdate) UnsetName()`

UnsetName ensures that no value is present for Name, not even an explicit nil
### GetEmail

`func (o *UserProfileUpdate) GetEmail() string`

GetEmail returns the Email field if non-nil, zero value otherwise.

### GetEmailOk

`func (o *UserProfileUpdate) GetEmailOk() (*string, bool)`

GetEmailOk returns a tuple with the Email field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEmail

`func (o *UserProfileUpdate) SetEmail(v string)`

SetEmail sets Email field to given value.

### HasEmail

`func (o *UserProfileUpdate) HasEmail() bool`

HasEmail returns a boolean if a field has been set.

### SetEmailNil

`func (o *UserProfileUpdate) SetEmailNil(b bool)`

 SetEmailNil sets the value for Email to be an explicit nil

### UnsetEmail
`func (o *UserProfileUpdate) UnsetEmail()`

UnsetEmail ensures that no value is present for Email, not even an explicit nil
### GetPreferences

`func (o *UserProfileUpdate) GetPreferences() map[string]interface{}`

GetPreferences returns the Preferences field if non-nil, zero value otherwise.

### GetPreferencesOk

`func (o *UserProfileUpdate) GetPreferencesOk() (*map[string]interface{}, bool)`

GetPreferencesOk returns a tuple with the Preferences field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPreferences

`func (o *UserProfileUpdate) SetPreferences(v map[string]interface{})`

SetPreferences sets Preferences field to given value.

### HasPreferences

`func (o *UserProfileUpdate) HasPreferences() bool`

HasPreferences returns a boolean if a field has been set.

### SetPreferencesNil

`func (o *UserProfileUpdate) SetPreferencesNil(b bool)`

 SetPreferencesNil sets the value for Preferences to be an explicit nil

### UnsetPreferences
`func (o *UserProfileUpdate) UnsetPreferences()`

UnsetPreferences ensures that no value is present for Preferences, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
