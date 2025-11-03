# UserDataExport

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ExportId** | **string** | Unique export identifier | 
**ExportTimestamp** | **string** | ISO timestamp of export | 
**UserId** | **string** | User identifier | 
**Username** | **string** | Username | 
**Email** | **string** | User email address | 
**Profile** | Pointer to **map[string]interface{}** | User profile data | [optional] 
**Sessions** | Pointer to **[]map[string]interface{}** | Active and recent sessions | [optional] 
**Conversations** | Pointer to **[]map[string]interface{}** | Conversation history | [optional] 
**Preferences** | Pointer to **map[string]interface{}** | User preferences and settings | [optional] 
**AuditLog** | Pointer to **[]map[string]interface{}** | User activity audit log | [optional] 
**Consents** | Pointer to **[]map[string]interface{}** | Consent records | [optional] 
**Metadata** | Pointer to **map[string]interface{}** | Additional metadata | [optional] 

## Methods

### NewUserDataExport

`func NewUserDataExport(exportId string, exportTimestamp string, userId string, username string, email string, ) *UserDataExport`

NewUserDataExport instantiates a new UserDataExport object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewUserDataExportWithDefaults

`func NewUserDataExportWithDefaults() *UserDataExport`

NewUserDataExportWithDefaults instantiates a new UserDataExport object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetExportId

`func (o *UserDataExport) GetExportId() string`

GetExportId returns the ExportId field if non-nil, zero value otherwise.

### GetExportIdOk

`func (o *UserDataExport) GetExportIdOk() (*string, bool)`

GetExportIdOk returns a tuple with the ExportId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExportId

`func (o *UserDataExport) SetExportId(v string)`

SetExportId sets ExportId field to given value.


### GetExportTimestamp

`func (o *UserDataExport) GetExportTimestamp() string`

GetExportTimestamp returns the ExportTimestamp field if non-nil, zero value otherwise.

### GetExportTimestampOk

`func (o *UserDataExport) GetExportTimestampOk() (*string, bool)`

GetExportTimestampOk returns a tuple with the ExportTimestamp field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExportTimestamp

`func (o *UserDataExport) SetExportTimestamp(v string)`

SetExportTimestamp sets ExportTimestamp field to given value.


### GetUserId

`func (o *UserDataExport) GetUserId() string`

GetUserId returns the UserId field if non-nil, zero value otherwise.

### GetUserIdOk

`func (o *UserDataExport) GetUserIdOk() (*string, bool)`

GetUserIdOk returns a tuple with the UserId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUserId

`func (o *UserDataExport) SetUserId(v string)`

SetUserId sets UserId field to given value.


### GetUsername

`func (o *UserDataExport) GetUsername() string`

GetUsername returns the Username field if non-nil, zero value otherwise.

### GetUsernameOk

`func (o *UserDataExport) GetUsernameOk() (*string, bool)`

GetUsernameOk returns a tuple with the Username field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUsername

`func (o *UserDataExport) SetUsername(v string)`

SetUsername sets Username field to given value.


### GetEmail

`func (o *UserDataExport) GetEmail() string`

GetEmail returns the Email field if non-nil, zero value otherwise.

### GetEmailOk

`func (o *UserDataExport) GetEmailOk() (*string, bool)`

GetEmailOk returns a tuple with the Email field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEmail

`func (o *UserDataExport) SetEmail(v string)`

SetEmail sets Email field to given value.


### GetProfile

`func (o *UserDataExport) GetProfile() map[string]interface{}`

GetProfile returns the Profile field if non-nil, zero value otherwise.

### GetProfileOk

`func (o *UserDataExport) GetProfileOk() (*map[string]interface{}, bool)`

GetProfileOk returns a tuple with the Profile field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProfile

`func (o *UserDataExport) SetProfile(v map[string]interface{})`

SetProfile sets Profile field to given value.

### HasProfile

`func (o *UserDataExport) HasProfile() bool`

HasProfile returns a boolean if a field has been set.

### GetSessions

`func (o *UserDataExport) GetSessions() []*map[string]interface{}`

GetSessions returns the Sessions field if non-nil, zero value otherwise.

### GetSessionsOk

`func (o *UserDataExport) GetSessionsOk() (*[]*map[string]interface{}, bool)`

GetSessionsOk returns a tuple with the Sessions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSessions

`func (o *UserDataExport) SetSessions(v []*map[string]interface{})`

SetSessions sets Sessions field to given value.

### HasSessions

`func (o *UserDataExport) HasSessions() bool`

HasSessions returns a boolean if a field has been set.

### GetConversations

`func (o *UserDataExport) GetConversations() []*map[string]interface{}`

GetConversations returns the Conversations field if non-nil, zero value otherwise.

### GetConversationsOk

`func (o *UserDataExport) GetConversationsOk() (*[]*map[string]interface{}, bool)`

GetConversationsOk returns a tuple with the Conversations field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConversations

`func (o *UserDataExport) SetConversations(v []*map[string]interface{})`

SetConversations sets Conversations field to given value.

### HasConversations

`func (o *UserDataExport) HasConversations() bool`

HasConversations returns a boolean if a field has been set.

### GetPreferences

`func (o *UserDataExport) GetPreferences() map[string]interface{}`

GetPreferences returns the Preferences field if non-nil, zero value otherwise.

### GetPreferencesOk

`func (o *UserDataExport) GetPreferencesOk() (*map[string]interface{}, bool)`

GetPreferencesOk returns a tuple with the Preferences field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPreferences

`func (o *UserDataExport) SetPreferences(v map[string]interface{})`

SetPreferences sets Preferences field to given value.

### HasPreferences

`func (o *UserDataExport) HasPreferences() bool`

HasPreferences returns a boolean if a field has been set.

### GetAuditLog

`func (o *UserDataExport) GetAuditLog() []*map[string]interface{}`

GetAuditLog returns the AuditLog field if non-nil, zero value otherwise.

### GetAuditLogOk

`func (o *UserDataExport) GetAuditLogOk() (*[]*map[string]interface{}, bool)`

GetAuditLogOk returns a tuple with the AuditLog field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuditLog

`func (o *UserDataExport) SetAuditLog(v []*map[string]interface{})`

SetAuditLog sets AuditLog field to given value.

### HasAuditLog

`func (o *UserDataExport) HasAuditLog() bool`

HasAuditLog returns a boolean if a field has been set.

### GetConsents

`func (o *UserDataExport) GetConsents() []*map[string]interface{}`

GetConsents returns the Consents field if non-nil, zero value otherwise.

### GetConsentsOk

`func (o *UserDataExport) GetConsentsOk() (*[]*map[string]interface{}, bool)`

GetConsentsOk returns a tuple with the Consents field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConsents

`func (o *UserDataExport) SetConsents(v []*map[string]interface{})`

SetConsents sets Consents field to given value.

### HasConsents

`func (o *UserDataExport) HasConsents() bool`

HasConsents returns a boolean if a field has been set.

### GetMetadata

`func (o *UserDataExport) GetMetadata() map[string]interface{}`

GetMetadata returns the Metadata field if non-nil, zero value otherwise.

### GetMetadataOk

`func (o *UserDataExport) GetMetadataOk() (*map[string]interface{}, bool)`

GetMetadataOk returns a tuple with the Metadata field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMetadata

`func (o *UserDataExport) SetMetadata(v map[string]interface{})`

SetMetadata sets Metadata field to given value.

### HasMetadata

`func (o *UserDataExport) HasMetadata() bool`

HasMetadata returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


