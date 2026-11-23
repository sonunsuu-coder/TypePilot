# TypePilot for Android

The Android project is generated with Capacitor and opens the production TypePilot site in its app window.

## Build a debug APK

1. Install Android Studio and Android SDK Platform 35 (including Build Tools 35.0.0).
2. Install JDK 21 (required by the generated Capacitor Android project).
3. From this folder run `npm install`, `npx cap sync android`, then `cd android` and `gradlew.bat assembleDebug`.
4. The APK is created at `android/app/build/outputs/apk/debug/app-debug.apk`.

The APK needs an internet connection because lessons and the API are served by the production site. The PWA caches the app shell, but lesson and typing APIs still require connectivity.

To open the native project in Android Studio, run `npx cap open android`.
