## mcp-client@2.8.0

This generator creates TypeScript/JavaScript client that utilizes [axios](https://github.com/axios/axios). The generated Node module can be used in the following environments:

Environment
* Node.js
* Webpack
* Browserify

Language level
* ES5 - you must have a Promises/A+ library installed
* ES6

Module system
* CommonJS
* ES6 module system

It can be used in both TypeScript and JavaScript. In TypeScript, the definition will be automatically resolved via `package.json`. ([Reference](https://www.typescriptlang.org/docs/handbook/declaration-files/consumption.html))

### Building

To build and compile the typescript sources to javascript use:
```
npm install
npm run build
```

### Publishing

First build the package then run `npm publish`

### Consuming

navigate to the folder of your consuming project and run one of the following commands.

_published:_

```
npm install mcp-client@2.8.0 --save
```

_unPublished (not recommended):_

```
npm install PATH_TO_GENERATED_PACKAGE --save
```

### Documentation for API Endpoints

All URIs are relative to *http://localhost*

Class | Method | HTTP request | Description
------------ | ------------- | ------------- | -------------
*APIKeysApi* | [**createApiKeyApiV1ApiKeysPost**](docs/APIKeysApi.md#createapikeyapiv1apikeyspost) | **POST** /api/v1/api-keys/ | Create Api Key
*APIKeysApi* | [**listApiKeysApiV1ApiKeysGet**](docs/APIKeysApi.md#listapikeysapiv1apikeysget) | **GET** /api/v1/api-keys/ | List Api Keys
*APIKeysApi* | [**revokeApiKeyApiV1ApiKeysKeyIdDelete**](docs/APIKeysApi.md#revokeapikeyapiv1apikeyskeyiddelete) | **DELETE** /api/v1/api-keys/{key_id} | Revoke Api Key
*APIKeysApi* | [**rotateApiKeyApiV1ApiKeysKeyIdRotatePost**](docs/APIKeysApi.md#rotateapikeyapiv1apikeyskeyidrotatepost) | **POST** /api/v1/api-keys/{key_id}/rotate | Rotate Api Key
*APIMetadataApi* | [**getApiVersionMetadata**](docs/APIMetadataApi.md#getapiversionmetadata) | **GET** /api/version | Get API version information
*AuthApi* | [**loginAuthLoginPost**](docs/AuthApi.md#loginauthloginpost) | **POST** /auth/login | Login
*AuthApi* | [**refreshTokenAuthRefreshPost**](docs/AuthApi.md#refreshtokenauthrefreshpost) | **POST** /auth/refresh | Refresh Token
*DefaultApi* | [**handleMessageMessagePost**](docs/DefaultApi.md#handlemessagemessagepost) | **POST** /message | Handle Message
*DefaultApi* | [**listResourcesResourcesGet**](docs/DefaultApi.md#listresourcesresourcesget) | **GET** /resources | List Resources
*DefaultApi* | [**listToolsToolsGet**](docs/DefaultApi.md#listtoolstoolsget) | **GET** /tools | List Tools
*DefaultApi* | [**rootGet**](docs/DefaultApi.md#rootget) | **GET** / | Root
*GDPRComplianceApi* | [**deleteUserAccountApiV1UsersMeDelete**](docs/GDPRComplianceApi.md#deleteuseraccountapiv1usersmedelete) | **DELETE** /api/v1/users/me | Delete User Account
*GDPRComplianceApi* | [**exportUserDataApiV1UsersMeExportGet**](docs/GDPRComplianceApi.md#exportuserdataapiv1usersmeexportget) | **GET** /api/v1/users/me/export | Export User Data
*GDPRComplianceApi* | [**getConsentStatusApiV1UsersMeConsentGet**](docs/GDPRComplianceApi.md#getconsentstatusapiv1usersmeconsentget) | **GET** /api/v1/users/me/consent | Get Consent Status
*GDPRComplianceApi* | [**getUserDataApiV1UsersMeDataGet**](docs/GDPRComplianceApi.md#getuserdataapiv1usersmedataget) | **GET** /api/v1/users/me/data | Get User Data
*GDPRComplianceApi* | [**updateConsentApiV1UsersMeConsentPost**](docs/GDPRComplianceApi.md#updateconsentapiv1usersmeconsentpost) | **POST** /api/v1/users/me/consent | Update Consent
*GDPRComplianceApi* | [**updateUserProfileApiV1UsersMePatch**](docs/GDPRComplianceApi.md#updateuserprofileapiv1usersmepatch) | **PATCH** /api/v1/users/me | Update User Profile
*SCIM20Api* | [**createGroupScimV2GroupsPost**](docs/SCIM20Api.md#creategroupscimv2groupspost) | **POST** /scim/v2/Groups | Create Group
*SCIM20Api* | [**createUserScimV2UsersPost**](docs/SCIM20Api.md#createuserscimv2userspost) | **POST** /scim/v2/Users | Create User
*SCIM20Api* | [**deleteUserScimV2UsersUserIdDelete**](docs/SCIM20Api.md#deleteuserscimv2usersuseriddelete) | **DELETE** /scim/v2/Users/{user_id} | Delete User
*SCIM20Api* | [**getGroupScimV2GroupsGroupIdGet**](docs/SCIM20Api.md#getgroupscimv2groupsgroupidget) | **GET** /scim/v2/Groups/{group_id} | Get Group
*SCIM20Api* | [**getUserScimV2UsersUserIdGet**](docs/SCIM20Api.md#getuserscimv2usersuseridget) | **GET** /scim/v2/Users/{user_id} | Get User
*SCIM20Api* | [**listUsersScimV2UsersGet**](docs/SCIM20Api.md#listusersscimv2usersget) | **GET** /scim/v2/Users | List Users
*SCIM20Api* | [**replaceUserScimV2UsersUserIdPut**](docs/SCIM20Api.md#replaceuserscimv2usersuseridput) | **PUT** /scim/v2/Users/{user_id} | Replace User
*SCIM20Api* | [**updateUserScimV2UsersUserIdPatch**](docs/SCIM20Api.md#updateuserscimv2usersuseridpatch) | **PATCH** /scim/v2/Users/{user_id} | Update User
*ServicePrincipalsApi* | [**associateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost**](docs/ServicePrincipalsApi.md#associateserviceprincipalwithuserapiv1serviceprincipalsserviceidassociateuserpost) | **POST** /api/v1/service-principals/{service_id}/associate-user | Associate Service Principal With User
*ServicePrincipalsApi* | [**createServicePrincipalApiV1ServicePrincipalsPost**](docs/ServicePrincipalsApi.md#createserviceprincipalapiv1serviceprincipalspost) | **POST** /api/v1/service-principals/ | Create Service Principal
*ServicePrincipalsApi* | [**deleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete**](docs/ServicePrincipalsApi.md#deleteserviceprincipalapiv1serviceprincipalsserviceiddelete) | **DELETE** /api/v1/service-principals/{service_id} | Delete Service Principal
*ServicePrincipalsApi* | [**getServicePrincipalApiV1ServicePrincipalsServiceIdGet**](docs/ServicePrincipalsApi.md#getserviceprincipalapiv1serviceprincipalsserviceidget) | **GET** /api/v1/service-principals/{service_id} | Get Service Principal
*ServicePrincipalsApi* | [**listServicePrincipalsApiV1ServicePrincipalsGet**](docs/ServicePrincipalsApi.md#listserviceprincipalsapiv1serviceprincipalsget) | **GET** /api/v1/service-principals/ | List Service Principals
*ServicePrincipalsApi* | [**rotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost**](docs/ServicePrincipalsApi.md#rotateserviceprincipalsecretapiv1serviceprincipalsserviceidrotatesecretpost) | **POST** /api/v1/service-principals/{service_id}/rotate-secret | Rotate Service Principal Secret


### Documentation For Models

 - [APIKeyResponse](docs/APIKeyResponse.md)
 - [APIVersionInfo](docs/APIVersionInfo.md)
 - [BodyCreateApiKeyApiV1ApiKeysPost](docs/BodyCreateApiKeyApiV1ApiKeysPost.md)
 - [BodyCreateGroupScimV2GroupsPost](docs/BodyCreateGroupScimV2GroupsPost.md)
 - [BodyCreateServicePrincipalApiV1ServicePrincipalsPost](docs/BodyCreateServicePrincipalApiV1ServicePrincipalsPost.md)
 - [BodyCreateUserScimV2UsersPost](docs/BodyCreateUserScimV2UsersPost.md)
 - [BodyReplaceUserScimV2UsersUserIdPut](docs/BodyReplaceUserScimV2UsersUserIdPut.md)
 - [BodyUpdateConsentApiV1UsersMeConsentPost](docs/BodyUpdateConsentApiV1UsersMeConsentPost.md)
 - [BodyUpdateUserProfileApiV1UsersMePatch](docs/BodyUpdateUserProfileApiV1UsersMePatch.md)
 - [BodyUpdateUserScimV2UsersUserIdPatch](docs/BodyUpdateUserScimV2UsersUserIdPatch.md)
 - [ConsentRecord](docs/ConsentRecord.md)
 - [ConsentResponse](docs/ConsentResponse.md)
 - [ConsentType](docs/ConsentType.md)
 - [CreateAPIKeyRequest](docs/CreateAPIKeyRequest.md)
 - [CreateAPIKeyResponse](docs/CreateAPIKeyResponse.md)
 - [CreateServicePrincipalRequest](docs/CreateServicePrincipalRequest.md)
 - [CreateServicePrincipalResponse](docs/CreateServicePrincipalResponse.md)
 - [HTTPAuthorizationCredentials](docs/HTTPAuthorizationCredentials.md)
 - [HTTPValidationError](docs/HTTPValidationError.md)
 - [LoginRequest](docs/LoginRequest.md)
 - [LoginResponse](docs/LoginResponse.md)
 - [RefreshTokenRequest](docs/RefreshTokenRequest.md)
 - [RefreshTokenResponse](docs/RefreshTokenResponse.md)
 - [RotateAPIKeyResponse](docs/RotateAPIKeyResponse.md)
 - [RotateSecretResponse](docs/RotateSecretResponse.md)
 - [SCIMAddress](docs/SCIMAddress.md)
 - [SCIMEmail](docs/SCIMEmail.md)
 - [SCIMEnterpriseUser](docs/SCIMEnterpriseUser.md)
 - [SCIMGroup](docs/SCIMGroup.md)
 - [SCIMGroupMembership](docs/SCIMGroupMembership.md)
 - [SCIMListResponse](docs/SCIMListResponse.md)
 - [SCIMMember](docs/SCIMMember.md)
 - [SCIMName](docs/SCIMName.md)
 - [SCIMPatchOp](docs/SCIMPatchOp.md)
 - [SCIMPatchOperation](docs/SCIMPatchOperation.md)
 - [SCIMPatchRequest](docs/SCIMPatchRequest.md)
 - [SCIMPhoneNumber](docs/SCIMPhoneNumber.md)
 - [SCIMUser](docs/SCIMUser.md)
 - [ServicePrincipalResponse](docs/ServicePrincipalResponse.md)
 - [UserDataExport](docs/UserDataExport.md)
 - [UserProfileUpdate](docs/UserProfileUpdate.md)
 - [ValidationError](docs/ValidationError.md)
 - [ValidationErrorLocInner](docs/ValidationErrorLocInner.md)


<a id="documentation-for-authorization"></a>
## Documentation For Authorization

Endpoints do not require authorization.

