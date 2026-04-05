


curl -X POST https://oie-8764513.oktapreview.com/oauth2/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<OKTA_CLIENT_ID>" \
  -d "client_secret=<OKTA_CLIENT_SECRET>" \
  -d "scope=okta.users.read"


  curl -X POST https://oie-8764513.oktapreview.com/oauth2/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=0oax4b20kdBGCVvMk1d7" \
  -d "client_secret=q-oEtQhGhWKGT3uW3hZOPxeLjcdSDZT9nMZA1SsAQMttAKXLr8nhbqRLqzubTKyH \
  -d "scope=okta.users.read"

,"token_endpoint":"https://oie-8764513.oktapreview.com/oauth2/default/v1/token","registration_endpoint":"https://oie-

  # Note the /oauth2/{authServerId}/ path
curl -X POST https://oie-8764513.oktapreview.com/oauth2/default/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=0oax4b20kdBGCVvMk1d7" \
  -d "client_secret=YOUR_SECRET" \
  -d "scope=your.custom.scope"



  {"issuer":"https://oie-8764513.oktapreview.com/oauth2/default","authorization_endpoint":"https://oie-8764513.oktapreview.com/oauth2/default/v1/authorize","token_endpoint":"https://oie-8764513.oktapreview.com/oauth2/default/v1/token","registration_endpoint":"https://oie-8764513.oktapreview.com/oauth2/v1/clients","jwks_uri":"https://oie-8764513.oktapreview.com/oauth2/default/v1/keys","response_types_supported":["code","token","id_token","code id_token","code token","id_token token","code id_token token"],"response_modes_supported":["query","fragment","form_post","okta_post_message"],"grant_types_supported":["authorization_code","implicit","refresh_token","password","client_credentials","urn:ietf:params:oauth:grant-type:device_code","urn:openid:params:grant-type:ciba","urn:okta:params:oauth:grant-type:otp","http://auth0.com/oauth/grant-type/mfa-otp","urn:okta:params:oauth:grant-type:oob","http://auth0.com/oauth/grant-type/mfa-oob"],"subject_types_supported":["public"],"scopes_supported":["okta.myAccount.appAuthenticator.maintenance.manage","okta.myAccount.appAuthenticator.maintenance.read","okta.myAccount.appAuthenticator.manage","okta.myAccount.appAuthenticator.read","okta.myAccount.authenticators.manage","okta.myAccount.authenticators.read","okta.myAccount.email.manage","okta.myAccount.email.read","okta.myAccount.manage","okta.myAccount.oktaApplications.read","okta.myAccount.organization.read","okta.myAccount.phone.manage","okta.myAccount.phone.read","okta.myAccount.profile.manage","okta.myAccount.profile.read","okta.myAccount.read","pricing","read:messages","resource.read","write:messages","openid","profile","email","address","phone","offline_access","device_sso"],"token_endpoint_auth_methods_supported":["client_secret_basic","client_secret_post","client_secret_jwt","private_key_jwt","none"],"claims_supported":["ver","jti","iss","aud","iat","exp","cid","uid","scp","sub"],"code_challenge_methods_supported":["S256"],"introspection_endpoint":"https://oie-8764513.oktapreview.com/oauth2/default/v1/introspect","introspection_endpoint_auth_methods_supported":["client_secret_basic","client_secret_post","client_secret_jwt","private_key_jwt","none"],"revocation_endpoint":"https://oie-8764513.oktapreview.com/oauth2/default/v1/revoke","revocation_endpoint_auth_methods_supported":["client_secret_basic","client_secret_post","client_secret_jwt","private_key_jwt","none"],"end_session_endpoint":"https://oie-8764513.oktapreview.com/oauth2/default/v1/logout","request_parameter_supported":true,"request_object_signing_alg_values_supported":["HS256","HS384","HS512","RS256","RS384","RS512","ES256","ES384","ES512"],"device_authorization_endpoint":"https://oie-8764513.oktapreview.com/oauth2/default/v1/device/authorize","pushed_authorization_request_endpoint":"https://oie-8764513.oktapreview.com/oauth2/default/v1/par","backchannel_token_delivery_modes_supported":["poll"],"backchannel_authentication_request_signing_alg_values_supported":["HS256","HS384","HS512","RS256","RS384","RS512","ES256","ES384","ES512"],"dpop_signing_alg_values_supported":["RS256","RS384","RS512","ES256","ES384","ES512"]}