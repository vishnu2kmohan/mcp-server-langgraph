# \GDPRComplianceAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**DeleteUserAccountApiV1UsersMeDelete**](GDPRComplianceAPI.md#DeleteUserAccountApiV1UsersMeDelete) | **Delete** /api/v1/users/me | Delete User Account
[**ExportUserDataApiV1UsersMeExportGet**](GDPRComplianceAPI.md#ExportUserDataApiV1UsersMeExportGet) | **Get** /api/v1/users/me/export | Export User Data
[**GetConsentStatusApiV1UsersMeConsentGet**](GDPRComplianceAPI.md#GetConsentStatusApiV1UsersMeConsentGet) | **Get** /api/v1/users/me/consent | Get Consent Status
[**GetUserDataApiV1UsersMeDataGet**](GDPRComplianceAPI.md#GetUserDataApiV1UsersMeDataGet) | **Get** /api/v1/users/me/data | Get User Data
[**UpdateConsentApiV1UsersMeConsentPost**](GDPRComplianceAPI.md#UpdateConsentApiV1UsersMeConsentPost) | **Post** /api/v1/users/me/consent | Update Consent
[**UpdateUserProfileApiV1UsersMePatch**](GDPRComplianceAPI.md#UpdateUserProfileApiV1UsersMePatch) | **Patch** /api/v1/users/me | Update User Profile



## DeleteUserAccountApiV1UsersMeDelete

> map[string]interface{} DeleteUserAccountApiV1UsersMeDelete(ctx).Confirm(confirm).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Delete User Account



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	confirm := true // bool | Must be true to confirm account deletion
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GDPRComplianceAPI.DeleteUserAccountApiV1UsersMeDelete(context.Background()).Confirm(confirm).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GDPRComplianceAPI.DeleteUserAccountApiV1UsersMeDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DeleteUserAccountApiV1UsersMeDelete`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `GDPRComplianceAPI.DeleteUserAccountApiV1UsersMeDelete`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiDeleteUserAccountApiV1UsersMeDeleteRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **confirm** | **bool** | Must be true to confirm account deletion |
 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  |

### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ExportUserDataApiV1UsersMeExportGet

> interface{} ExportUserDataApiV1UsersMeExportGet(ctx).Format(format).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Export User Data



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	format := "format_example" // string | Export format: json or csv (optional) (default to "json")
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GDPRComplianceAPI.ExportUserDataApiV1UsersMeExportGet(context.Background()).Format(format).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GDPRComplianceAPI.ExportUserDataApiV1UsersMeExportGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ExportUserDataApiV1UsersMeExportGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `GDPRComplianceAPI.ExportUserDataApiV1UsersMeExportGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiExportUserDataApiV1UsersMeExportGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **format** | **string** | Export format: json or csv | [default to &quot;json&quot;]
 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  |

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetConsentStatusApiV1UsersMeConsentGet

> ConsentResponse GetConsentStatusApiV1UsersMeConsentGet(ctx).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Get Consent Status



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GDPRComplianceAPI.GetConsentStatusApiV1UsersMeConsentGet(context.Background()).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GDPRComplianceAPI.GetConsentStatusApiV1UsersMeConsentGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetConsentStatusApiV1UsersMeConsentGet`: ConsentResponse
	fmt.Fprintf(os.Stdout, "Response from `GDPRComplianceAPI.GetConsentStatusApiV1UsersMeConsentGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetConsentStatusApiV1UsersMeConsentGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  |

### Return type

[**ConsentResponse**](ConsentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetUserDataApiV1UsersMeDataGet

> UserDataExport GetUserDataApiV1UsersMeDataGet(ctx).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Get User Data



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GDPRComplianceAPI.GetUserDataApiV1UsersMeDataGet(context.Background()).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GDPRComplianceAPI.GetUserDataApiV1UsersMeDataGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetUserDataApiV1UsersMeDataGet`: UserDataExport
	fmt.Fprintf(os.Stdout, "Response from `GDPRComplianceAPI.GetUserDataApiV1UsersMeDataGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetUserDataApiV1UsersMeDataGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  |

### Return type

[**UserDataExport**](UserDataExport.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## UpdateConsentApiV1UsersMeConsentPost

> ConsentResponse UpdateConsentApiV1UsersMeConsentPost(ctx).BodyUpdateConsentApiV1UsersMeConsentPost(bodyUpdateConsentApiV1UsersMeConsentPost).Execute()

Update Consent



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	bodyUpdateConsentApiV1UsersMeConsentPost := *openapiclient.NewBodyUpdateConsentApiV1UsersMeConsentPost(*openapiclient.NewConsentRecord(openapiclient.ConsentType("analytics"), false)) // BodyUpdateConsentApiV1UsersMeConsentPost |

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GDPRComplianceAPI.UpdateConsentApiV1UsersMeConsentPost(context.Background()).BodyUpdateConsentApiV1UsersMeConsentPost(bodyUpdateConsentApiV1UsersMeConsentPost).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GDPRComplianceAPI.UpdateConsentApiV1UsersMeConsentPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `UpdateConsentApiV1UsersMeConsentPost`: ConsentResponse
	fmt.Fprintf(os.Stdout, "Response from `GDPRComplianceAPI.UpdateConsentApiV1UsersMeConsentPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiUpdateConsentApiV1UsersMeConsentPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **bodyUpdateConsentApiV1UsersMeConsentPost** | [**BodyUpdateConsentApiV1UsersMeConsentPost**](BodyUpdateConsentApiV1UsersMeConsentPost.md) |  |

### Return type

[**ConsentResponse**](ConsentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## UpdateUserProfileApiV1UsersMePatch

> map[string]interface{} UpdateUserProfileApiV1UsersMePatch(ctx).BodyUpdateUserProfileApiV1UsersMePatch(bodyUpdateUserProfileApiV1UsersMePatch).Execute()

Update User Profile



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	bodyUpdateUserProfileApiV1UsersMePatch := *openapiclient.NewBodyUpdateUserProfileApiV1UsersMePatch(*openapiclient.NewUserProfileUpdate()) // BodyUpdateUserProfileApiV1UsersMePatch |

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GDPRComplianceAPI.UpdateUserProfileApiV1UsersMePatch(context.Background()).BodyUpdateUserProfileApiV1UsersMePatch(bodyUpdateUserProfileApiV1UsersMePatch).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GDPRComplianceAPI.UpdateUserProfileApiV1UsersMePatch``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `UpdateUserProfileApiV1UsersMePatch`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `GDPRComplianceAPI.UpdateUserProfileApiV1UsersMePatch`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiUpdateUserProfileApiV1UsersMePatchRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **bodyUpdateUserProfileApiV1UsersMePatch** | [**BodyUpdateUserProfileApiV1UsersMePatch**](BodyUpdateUserProfileApiV1UsersMePatch.md) |  |

### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)
