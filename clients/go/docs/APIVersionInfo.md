# APIVersionInfo

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Version** | **string** | Application version (semantic versioning: MAJOR.MINOR.PATCH) | 
**ApiVersion** | **string** | Current API version (e.g., &#39;v1&#39;) | 
**SupportedVersions** | **[]string** | List of supported API versions | 
**DeprecatedVersions** | Pointer to **[]string** | List of deprecated API versions (still functional but will be removed) | [optional] 
**SunsetDates** | Pointer to **map[string]string** | Sunset dates for deprecated versions (ISO 8601 format) | [optional] 
**ChangelogUrl** | Pointer to **NullableString** |  | [optional] 
**DocumentationUrl** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewAPIVersionInfo

`func NewAPIVersionInfo(version string, apiVersion string, supportedVersions []string, ) *APIVersionInfo`

NewAPIVersionInfo instantiates a new APIVersionInfo object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewAPIVersionInfoWithDefaults

`func NewAPIVersionInfoWithDefaults() *APIVersionInfo`

NewAPIVersionInfoWithDefaults instantiates a new APIVersionInfo object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetVersion

`func (o *APIVersionInfo) GetVersion() string`

GetVersion returns the Version field if non-nil, zero value otherwise.

### GetVersionOk

`func (o *APIVersionInfo) GetVersionOk() (*string, bool)`

GetVersionOk returns a tuple with the Version field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVersion

`func (o *APIVersionInfo) SetVersion(v string)`

SetVersion sets Version field to given value.


### GetApiVersion

`func (o *APIVersionInfo) GetApiVersion() string`

GetApiVersion returns the ApiVersion field if non-nil, zero value otherwise.

### GetApiVersionOk

`func (o *APIVersionInfo) GetApiVersionOk() (*string, bool)`

GetApiVersionOk returns a tuple with the ApiVersion field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetApiVersion

`func (o *APIVersionInfo) SetApiVersion(v string)`

SetApiVersion sets ApiVersion field to given value.


### GetSupportedVersions

`func (o *APIVersionInfo) GetSupportedVersions() []string`

GetSupportedVersions returns the SupportedVersions field if non-nil, zero value otherwise.

### GetSupportedVersionsOk

`func (o *APIVersionInfo) GetSupportedVersionsOk() (*[]string, bool)`

GetSupportedVersionsOk returns a tuple with the SupportedVersions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSupportedVersions

`func (o *APIVersionInfo) SetSupportedVersions(v []string)`

SetSupportedVersions sets SupportedVersions field to given value.


### GetDeprecatedVersions

`func (o *APIVersionInfo) GetDeprecatedVersions() []string`

GetDeprecatedVersions returns the DeprecatedVersions field if non-nil, zero value otherwise.

### GetDeprecatedVersionsOk

`func (o *APIVersionInfo) GetDeprecatedVersionsOk() (*[]string, bool)`

GetDeprecatedVersionsOk returns a tuple with the DeprecatedVersions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeprecatedVersions

`func (o *APIVersionInfo) SetDeprecatedVersions(v []string)`

SetDeprecatedVersions sets DeprecatedVersions field to given value.

### HasDeprecatedVersions

`func (o *APIVersionInfo) HasDeprecatedVersions() bool`

HasDeprecatedVersions returns a boolean if a field has been set.

### GetSunsetDates

`func (o *APIVersionInfo) GetSunsetDates() map[string]string`

GetSunsetDates returns the SunsetDates field if non-nil, zero value otherwise.

### GetSunsetDatesOk

`func (o *APIVersionInfo) GetSunsetDatesOk() (*map[string]string, bool)`

GetSunsetDatesOk returns a tuple with the SunsetDates field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSunsetDates

`func (o *APIVersionInfo) SetSunsetDates(v map[string]string)`

SetSunsetDates sets SunsetDates field to given value.

### HasSunsetDates

`func (o *APIVersionInfo) HasSunsetDates() bool`

HasSunsetDates returns a boolean if a field has been set.

### GetChangelogUrl

`func (o *APIVersionInfo) GetChangelogUrl() string`

GetChangelogUrl returns the ChangelogUrl field if non-nil, zero value otherwise.

### GetChangelogUrlOk

`func (o *APIVersionInfo) GetChangelogUrlOk() (*string, bool)`

GetChangelogUrlOk returns a tuple with the ChangelogUrl field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetChangelogUrl

`func (o *APIVersionInfo) SetChangelogUrl(v string)`

SetChangelogUrl sets ChangelogUrl field to given value.

### HasChangelogUrl

`func (o *APIVersionInfo) HasChangelogUrl() bool`

HasChangelogUrl returns a boolean if a field has been set.

### SetChangelogUrlNil

`func (o *APIVersionInfo) SetChangelogUrlNil(b bool)`

 SetChangelogUrlNil sets the value for ChangelogUrl to be an explicit nil

### UnsetChangelogUrl
`func (o *APIVersionInfo) UnsetChangelogUrl()`

UnsetChangelogUrl ensures that no value is present for ChangelogUrl, not even an explicit nil
### GetDocumentationUrl

`func (o *APIVersionInfo) GetDocumentationUrl() string`

GetDocumentationUrl returns the DocumentationUrl field if non-nil, zero value otherwise.

### GetDocumentationUrlOk

`func (o *APIVersionInfo) GetDocumentationUrlOk() (*string, bool)`

GetDocumentationUrlOk returns a tuple with the DocumentationUrl field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDocumentationUrl

`func (o *APIVersionInfo) SetDocumentationUrl(v string)`

SetDocumentationUrl sets DocumentationUrl field to given value.

### HasDocumentationUrl

`func (o *APIVersionInfo) HasDocumentationUrl() bool`

HasDocumentationUrl returns a boolean if a field has been set.

### SetDocumentationUrlNil

`func (o *APIVersionInfo) SetDocumentationUrlNil(b bool)`

 SetDocumentationUrlNil sets the value for DocumentationUrl to be an explicit nil

### UnsetDocumentationUrl
`func (o *APIVersionInfo) UnsetDocumentationUrl()`

UnsetDocumentationUrl ensures that no value is present for DocumentationUrl, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


