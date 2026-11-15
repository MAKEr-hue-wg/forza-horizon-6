[app]
title = Forza Horizon 6
package.name = forzahorizon6
package.domain = org.game.fh6
source.dir = .
source.include_exts = py,png,jpg,glb,gltf,wav,json,ttf
version = 1.0
requirements = python3,panda3d
orientation = landscape
fullscreen = 1
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
