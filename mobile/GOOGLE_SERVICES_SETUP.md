# Android Google Services setup (kept out of Git)

`google-services.json` is intentionally not committed to this repository because GitHub secret scanning detected a Google API key in the previous file.

1. In Firebase Console, rotate/restrict the previously exposed API key before reusing it.
2. Download a fresh `google-services.json` for the Android app `com.aadit23.voxmate`.
3. Place it at `mobile/google-services.json` locally.
4. This file is ignored by Git (`mobile/google-services.json` and `**/google-services.json`).
5. Never paste the API key into source code, `.env` files that are committed, documentation, issues, or pull requests.

The Expo app configuration no longer requires this file to be present in Git.
