[app]

allow_root = True

title = 金价监控
package.name = goldprice
package.domain = org.goldmonitor
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttc,ttf,otf
source.include_patterns = fonts/*
version = 1.0
requirements = python3,kivy,android,pyjnius,urllib3,requests,charset_normalizer,idna,certifi
orientation = portrait

[buildozer]

log_level = 2
warn_on_root = 0

[app:android]

fullscreen = 0
android.api = 31
android.minapi = 21
android.sdk = 31
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a,armeabi-v7a
android.permissions = INTERNET,ACCESS_NETWORK_STATE,FOREGROUND_SERVICE,POST_NOTIFICATIONS,WAKE_LOCK

# 关键：禁用 Gradle daemon，增加内存
p4a.extra_args = --gradle-options=org.gradle.jvmargs=-Xmx4096m --gradle-options=org.gradle.daemon=false
