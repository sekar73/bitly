# Postman testing

1. In Postman, choose **Import** and select `bitly.postman_collection.json` and `bitly.postman_environment.json` from this directory.
2. Select the **Bitly Lab — Local (change base_url for AWS)** environment.
3. Confirm `base_url` is `http://localhost:8000` (no trailing slash).
4. Open the collection's **Run** action and run all folders in order with one iteration. Alternatively, send requests individually in their listed order.

Registration generates a fresh email and random password and stores them in your selected environment. Registration and login automatically save `access_token`; protected requests inherit the collection's Bearer JWT. Cross-user tests use a second token without replacing the first user's token. Tokens expire after 30 minutes: rerun Login to get a fresh token.

The collection includes 30 requests: separate backend health/schema checks, registration/login/me, generated URLs, listing/lookup, 302 redirects, updates/deletion, custom-alias conflicts, expiration validation, unauthenticated access rejection, and cross-user ownership checks. Each request asserts its expected status; additional assertions verify destinations, identity, service routing and ownership. The expiration example expires in one hour; the past-expiration request tests rejection at creation. This collection does not wait an hour to test runtime expiry (the automated Python suite tests that).

Redirect requests disable automatic redirect following using their per-request setting. If your Postman version still follows redirects, open the request's **Settings** and turn **Automatically follow redirects** off. Otherwise you will see the destination's response instead of the API's 302 status.

For AWS, use the documented SSH tunnel and change `base_url` to `http://localhost:8080`. If you use the restricted EC2 HTTP endpoint directly, use `http://PUBLIC_IP`; its security-group CIDR must allow your IP, and HTTP does not encrypt your password/JWT. Use the tunnel for authentication requests.

The lifecycle folders delete their own links when they finish successfully. Test accounts remain because there is no account-deletion API. Re-running registration intentionally creates new accounts. Use your isolated learning database. If you interrupt a run, finish its DELETE requests to remove its links.

To sign in as an existing user, set `email` and `password`, then send **Login — saves JWT**, skipping registration. To create your own custom requests, inherit collection authorization. Do not export/share an environment after running it without clearing passwords and tokens. The supplied environment contains no credentials.
