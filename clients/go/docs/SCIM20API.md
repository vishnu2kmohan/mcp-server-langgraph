# \SCIM20API

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**CreateGroupScimV2GroupsPost**](SCIM20API.md#CreateGroupScimV2GroupsPost) | **Post** /scim/v2/Groups | Create Group
[**CreateUserScimV2UsersPost**](SCIM20API.md#CreateUserScimV2UsersPost) | **Post** /scim/v2/Users | Create User
[**DeleteUserScimV2UsersUserIdDelete**](SCIM20API.md#DeleteUserScimV2UsersUserIdDelete) | **Delete** /scim/v2/Users/{user_id} | Delete User
[**GetGroupScimV2GroupsGroupIdGet**](SCIM20API.md#GetGroupScimV2GroupsGroupIdGet) | **Get** /scim/v2/Groups/{group_id} | Get Group
[**GetUserScimV2UsersUserIdGet**](SCIM20API.md#GetUserScimV2UsersUserIdGet) | **Get** /scim/v2/Users/{user_id} | Get User
[**ListUsersScimV2UsersGet**](SCIM20API.md#ListUsersScimV2UsersGet) | **Get** /scim/v2/Users | List Users
[**ReplaceUserScimV2UsersUserIdPut**](SCIM20API.md#ReplaceUserScimV2UsersUserIdPut) | **Put** /scim/v2/Users/{user_id} | Replace User
[**UpdateUserScimV2UsersUserIdPatch**](SCIM20API.md#UpdateUserScimV2UsersUserIdPatch) | **Patch** /scim/v2/Users/{user_id} | Update User



## CreateGroupScimV2GroupsPost

> SCIMGroup CreateGroupScimV2GroupsPost(ctx).BodyCreateGroupScimV2GroupsPost(bodyCreateGroupScimV2GroupsPost).Execute()

Create Group



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
	bodyCreateGroupScimV2GroupsPost := *openapiclient.NewBodyCreateGroupScimV2GroupsPost(map[string]interface{}{"key": interface{}(123)}) // BodyCreateGroupScimV2GroupsPost | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SCIM20API.CreateGroupScimV2GroupsPost(context.Background()).BodyCreateGroupScimV2GroupsPost(bodyCreateGroupScimV2GroupsPost).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SCIM20API.CreateGroupScimV2GroupsPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateGroupScimV2GroupsPost`: SCIMGroup
	fmt.Fprintf(os.Stdout, "Response from `SCIM20API.CreateGroupScimV2GroupsPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCreateGroupScimV2GroupsPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **bodyCreateGroupScimV2GroupsPost** | [**BodyCreateGroupScimV2GroupsPost**](BodyCreateGroupScimV2GroupsPost.md) |  | 

### Return type

[**SCIMGroup**](SCIMGroup.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## CreateUserScimV2UsersPost

> SCIMUser CreateUserScimV2UsersPost(ctx).BodyCreateUserScimV2UsersPost(bodyCreateUserScimV2UsersPost).Execute()

Create User



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
	bodyCreateUserScimV2UsersPost := *openapiclient.NewBodyCreateUserScimV2UsersPost(map[string]interface{}{"key": interface{}(123)}) // BodyCreateUserScimV2UsersPost | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SCIM20API.CreateUserScimV2UsersPost(context.Background()).BodyCreateUserScimV2UsersPost(bodyCreateUserScimV2UsersPost).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SCIM20API.CreateUserScimV2UsersPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateUserScimV2UsersPost`: SCIMUser
	fmt.Fprintf(os.Stdout, "Response from `SCIM20API.CreateUserScimV2UsersPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCreateUserScimV2UsersPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **bodyCreateUserScimV2UsersPost** | [**BodyCreateUserScimV2UsersPost**](BodyCreateUserScimV2UsersPost.md) |  | 

### Return type

[**SCIMUser**](SCIMUser.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## DeleteUserScimV2UsersUserIdDelete

> DeleteUserScimV2UsersUserIdDelete(ctx, userId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Delete User



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
	userId := "userId_example" // string | 
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	r, err := apiClient.SCIM20API.DeleteUserScimV2UsersUserIdDelete(context.Background(), userId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SCIM20API.DeleteUserScimV2UsersUserIdDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**userId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiDeleteUserScimV2UsersUserIdDeleteRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

 (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetGroupScimV2GroupsGroupIdGet

> SCIMGroup GetGroupScimV2GroupsGroupIdGet(ctx, groupId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Get Group



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
	groupId := "groupId_example" // string | 
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SCIM20API.GetGroupScimV2GroupsGroupIdGet(context.Background(), groupId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SCIM20API.GetGroupScimV2GroupsGroupIdGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetGroupScimV2GroupsGroupIdGet`: SCIMGroup
	fmt.Fprintf(os.Stdout, "Response from `SCIM20API.GetGroupScimV2GroupsGroupIdGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**groupId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetGroupScimV2GroupsGroupIdGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**SCIMGroup**](SCIMGroup.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetUserScimV2UsersUserIdGet

> SCIMUser GetUserScimV2UsersUserIdGet(ctx, userId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Get User



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
	userId := "userId_example" // string | 
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SCIM20API.GetUserScimV2UsersUserIdGet(context.Background(), userId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SCIM20API.GetUserScimV2UsersUserIdGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetUserScimV2UsersUserIdGet`: SCIMUser
	fmt.Fprintf(os.Stdout, "Response from `SCIM20API.GetUserScimV2UsersUserIdGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**userId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetUserScimV2UsersUserIdGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**SCIMUser**](SCIMUser.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListUsersScimV2UsersGet

> SCIMListResponse ListUsersScimV2UsersGet(ctx).Filter(filter).StartIndex(startIndex).Count(count).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

List Users



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
	filter := "filter_example" // string | SCIM filter expression (optional)
	startIndex := int32(56) // int32 | 1-based start index (optional) (default to 1)
	count := int32(56) // int32 | Number of results (optional) (default to 100)
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SCIM20API.ListUsersScimV2UsersGet(context.Background()).Filter(filter).StartIndex(startIndex).Count(count).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SCIM20API.ListUsersScimV2UsersGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListUsersScimV2UsersGet`: SCIMListResponse
	fmt.Fprintf(os.Stdout, "Response from `SCIM20API.ListUsersScimV2UsersGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListUsersScimV2UsersGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filter** | **string** | SCIM filter expression | 
 **startIndex** | **int32** | 1-based start index | [default to 1]
 **count** | **int32** | Number of results | [default to 100]
 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**SCIMListResponse**](SCIMListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ReplaceUserScimV2UsersUserIdPut

> SCIMUser ReplaceUserScimV2UsersUserIdPut(ctx, userId).BodyReplaceUserScimV2UsersUserIdPut(bodyReplaceUserScimV2UsersUserIdPut).Execute()

Replace User



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
	userId := "userId_example" // string | 
	bodyReplaceUserScimV2UsersUserIdPut := *openapiclient.NewBodyReplaceUserScimV2UsersUserIdPut(map[string]interface{}{"key": interface{}(123)}) // BodyReplaceUserScimV2UsersUserIdPut | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SCIM20API.ReplaceUserScimV2UsersUserIdPut(context.Background(), userId).BodyReplaceUserScimV2UsersUserIdPut(bodyReplaceUserScimV2UsersUserIdPut).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SCIM20API.ReplaceUserScimV2UsersUserIdPut``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ReplaceUserScimV2UsersUserIdPut`: SCIMUser
	fmt.Fprintf(os.Stdout, "Response from `SCIM20API.ReplaceUserScimV2UsersUserIdPut`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**userId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiReplaceUserScimV2UsersUserIdPutRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **bodyReplaceUserScimV2UsersUserIdPut** | [**BodyReplaceUserScimV2UsersUserIdPut**](BodyReplaceUserScimV2UsersUserIdPut.md) |  | 

### Return type

[**SCIMUser**](SCIMUser.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## UpdateUserScimV2UsersUserIdPatch

> SCIMUser UpdateUserScimV2UsersUserIdPatch(ctx, userId).BodyUpdateUserScimV2UsersUserIdPatch(bodyUpdateUserScimV2UsersUserIdPatch).Execute()

Update User



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
	userId := "userId_example" // string | 
	bodyUpdateUserScimV2UsersUserIdPatch := *openapiclient.NewBodyUpdateUserScimV2UsersUserIdPatch(*openapiclient.NewSCIMPatchRequest([]openapiclient.SCIMPatchOperation{*openapiclient.NewSCIMPatchOperation(openapiclient.SCIMPatchOp("add"))})) // BodyUpdateUserScimV2UsersUserIdPatch | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SCIM20API.UpdateUserScimV2UsersUserIdPatch(context.Background(), userId).BodyUpdateUserScimV2UsersUserIdPatch(bodyUpdateUserScimV2UsersUserIdPatch).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SCIM20API.UpdateUserScimV2UsersUserIdPatch``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `UpdateUserScimV2UsersUserIdPatch`: SCIMUser
	fmt.Fprintf(os.Stdout, "Response from `SCIM20API.UpdateUserScimV2UsersUserIdPatch`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**userId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiUpdateUserScimV2UsersUserIdPatchRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **bodyUpdateUserScimV2UsersUserIdPatch** | [**BodyUpdateUserScimV2UsersUserIdPatch**](BodyUpdateUserScimV2UsersUserIdPatch.md) |  | 

### Return type

[**SCIMUser**](SCIMUser.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

