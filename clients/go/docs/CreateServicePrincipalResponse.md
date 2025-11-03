# CreateServicePrincipalResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ServiceId** | **string** |  | 
**Name** | **string** |  | 
**Description** | **string** |  | 
**AuthenticationMode** | **string** |  | 
**AssociatedUserId** | **NullableString** |  | 
**OwnerUserId** | **NullableString** |  | 
**InheritPermissions** | **bool** |  | 
**Enabled** | **bool** |  | 
**CreatedAt** | **NullableString** |  | 
**ClientSecret** | **string** | Client secret (save securely, won&#39;t be shown again) | 
**Message** | Pointer to **string** |  | [optional] [default to "Service principal created successfully. Save the client_secret securely."]

## Methods

### NewCreateServicePrincipalResponse

`func NewCreateServicePrincipalResponse(serviceId string, name string, description string, authenticationMode string, associatedUserId NullableString, ownerUserId NullableString, inheritPermissions bool, enabled bool, createdAt NullableString, clientSecret string, ) *CreateServicePrincipalResponse`

NewCreateServicePrincipalResponse instantiates a new CreateServicePrincipalResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCreateServicePrincipalResponseWithDefaults

`func NewCreateServicePrincipalResponseWithDefaults() *CreateServicePrincipalResponse`

NewCreateServicePrincipalResponseWithDefaults instantiates a new CreateServicePrincipalResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetServiceId

`func (o *CreateServicePrincipalResponse) GetServiceId() string`

GetServiceId returns the ServiceId field if non-nil, zero value otherwise.

### GetServiceIdOk

`func (o *CreateServicePrincipalResponse) GetServiceIdOk() (*string, bool)`

GetServiceIdOk returns a tuple with the ServiceId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetServiceId

`func (o *CreateServicePrincipalResponse) SetServiceId(v string)`

SetServiceId sets ServiceId field to given value.


### GetName

`func (o *CreateServicePrincipalResponse) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *CreateServicePrincipalResponse) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *CreateServicePrincipalResponse) SetName(v string)`

SetName sets Name field to given value.


### GetDescription

`func (o *CreateServicePrincipalResponse) GetDescription() string`

GetDescription returns the Description field if non-nil, zero value otherwise.

### GetDescriptionOk

`func (o *CreateServicePrincipalResponse) GetDescriptionOk() (*string, bool)`

GetDescriptionOk returns a tuple with the Description field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDescription

`func (o *CreateServicePrincipalResponse) SetDescription(v string)`

SetDescription sets Description field to given value.


### GetAuthenticationMode

`func (o *CreateServicePrincipalResponse) GetAuthenticationMode() string`

GetAuthenticationMode returns the AuthenticationMode field if non-nil, zero value otherwise.

### GetAuthenticationModeOk

`func (o *CreateServicePrincipalResponse) GetAuthenticationModeOk() (*string, bool)`

GetAuthenticationModeOk returns a tuple with the AuthenticationMode field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuthenticationMode

`func (o *CreateServicePrincipalResponse) SetAuthenticationMode(v string)`

SetAuthenticationMode sets AuthenticationMode field to given value.


### GetAssociatedUserId

`func (o *CreateServicePrincipalResponse) GetAssociatedUserId() string`

GetAssociatedUserId returns the AssociatedUserId field if non-nil, zero value otherwise.

### GetAssociatedUserIdOk

`func (o *CreateServicePrincipalResponse) GetAssociatedUserIdOk() (*string, bool)`

GetAssociatedUserIdOk returns a tuple with the AssociatedUserId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAssociatedUserId

`func (o *CreateServicePrincipalResponse) SetAssociatedUserId(v string)`

SetAssociatedUserId sets AssociatedUserId field to given value.


### SetAssociatedUserIdNil

`func (o *CreateServicePrincipalResponse) SetAssociatedUserIdNil(b bool)`

 SetAssociatedUserIdNil sets the value for AssociatedUserId to be an explicit nil

### UnsetAssociatedUserId
`func (o *CreateServicePrincipalResponse) UnsetAssociatedUserId()`

UnsetAssociatedUserId ensures that no value is present for AssociatedUserId, not even an explicit nil
### GetOwnerUserId

`func (o *CreateServicePrincipalResponse) GetOwnerUserId() string`

GetOwnerUserId returns the OwnerUserId field if non-nil, zero value otherwise.

### GetOwnerUserIdOk

`func (o *CreateServicePrincipalResponse) GetOwnerUserIdOk() (*string, bool)`

GetOwnerUserIdOk returns a tuple with the OwnerUserId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOwnerUserId

`func (o *CreateServicePrincipalResponse) SetOwnerUserId(v string)`

SetOwnerUserId sets OwnerUserId field to given value.


### SetOwnerUserIdNil

`func (o *CreateServicePrincipalResponse) SetOwnerUserIdNil(b bool)`

 SetOwnerUserIdNil sets the value for OwnerUserId to be an explicit nil

### UnsetOwnerUserId
`func (o *CreateServicePrincipalResponse) UnsetOwnerUserId()`

UnsetOwnerUserId ensures that no value is present for OwnerUserId, not even an explicit nil
### GetInheritPermissions

`func (o *CreateServicePrincipalResponse) GetInheritPermissions() bool`

GetInheritPermissions returns the InheritPermissions field if non-nil, zero value otherwise.

### GetInheritPermissionsOk

`func (o *CreateServicePrincipalResponse) GetInheritPermissionsOk() (*bool, bool)`

GetInheritPermissionsOk returns a tuple with the InheritPermissions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInheritPermissions

`func (o *CreateServicePrincipalResponse) SetInheritPermissions(v bool)`

SetInheritPermissions sets InheritPermissions field to given value.


### GetEnabled

`func (o *CreateServicePrincipalResponse) GetEnabled() bool`

GetEnabled returns the Enabled field if non-nil, zero value otherwise.

### GetEnabledOk

`func (o *CreateServicePrincipalResponse) GetEnabledOk() (*bool, bool)`

GetEnabledOk returns a tuple with the Enabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEnabled

`func (o *CreateServicePrincipalResponse) SetEnabled(v bool)`

SetEnabled sets Enabled field to given value.


### GetCreatedAt

`func (o *CreateServicePrincipalResponse) GetCreatedAt() string`

GetCreatedAt returns the CreatedAt field if non-nil, zero value otherwise.

### GetCreatedAtOk

`func (o *CreateServicePrincipalResponse) GetCreatedAtOk() (*string, bool)`

GetCreatedAtOk returns a tuple with the CreatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedAt

`func (o *CreateServicePrincipalResponse) SetCreatedAt(v string)`

SetCreatedAt sets CreatedAt field to given value.


### SetCreatedAtNil

`func (o *CreateServicePrincipalResponse) SetCreatedAtNil(b bool)`

 SetCreatedAtNil sets the value for CreatedAt to be an explicit nil

### UnsetCreatedAt
`func (o *CreateServicePrincipalResponse) UnsetCreatedAt()`

UnsetCreatedAt ensures that no value is present for CreatedAt, not even an explicit nil
### GetClientSecret

`func (o *CreateServicePrincipalResponse) GetClientSecret() string`

GetClientSecret returns the ClientSecret field if non-nil, zero value otherwise.

### GetClientSecretOk

`func (o *CreateServicePrincipalResponse) GetClientSecretOk() (*string, bool)`

GetClientSecretOk returns a tuple with the ClientSecret field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetClientSecret

`func (o *CreateServicePrincipalResponse) SetClientSecret(v string)`

SetClientSecret sets ClientSecret field to given value.


### GetMessage

`func (o *CreateServicePrincipalResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *CreateServicePrincipalResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *CreateServicePrincipalResponse) SetMessage(v string)`

SetMessage sets Message field to given value.

### HasMessage

`func (o *CreateServicePrincipalResponse) HasMessage() bool`

HasMessage returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


