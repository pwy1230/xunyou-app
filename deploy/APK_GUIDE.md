# 寻尤APP - WebView APK打包指南

## 方案1：在线打包（推荐，最简单）

### WebIntoApp（免费，推荐）

1. 访问 https://www.webintoapp.com/
2. 点击 "Create App"
3. 填写配置：
   - **Website URL**: `https://你的用户名.pythonanywhere.com`
   - **App Name**: 寻尤
   - **Package Name**: com.xunyou.app
4. 高级设置：
   - ✅ Fullscreen（全屏，无地址栏）
   - ✅ Allow File Access
   - ✅ Allow Camera（如需拍照上传）
   - Screen Orientation: Portrait（竖屏）
5. 点击 "Build"，等待生成
6. 下载APK，安装到手机

### GoNative.io

1. 访问 https://gonative.io/
2. 输入URL：`https://你的用户名.pythonanywhere.com`
3. 配置APP名：寻尤
4. 下载APK

### AppsGeyser

1. 访问 https://appsgeyser.com/
2. 选择 "Website" 模板
3. 输入URL和APP名
4. 生成APK

---

## 方案2：Android Studio项目（需要电脑有Android Studio）

项目已生成在 `deploy/android-studio/` 目录下，可直接用Android Studio打开编译。

### 使用步骤：

1. 安装 Android Studio: https://developer.android.com/studio
2. 打开项目: File → Open → 选择 `deploy/android-studio/` 目录
3. 等待Gradle同步完成
4. 修改 `app/src/main/java/com/xunyou/app/MainActivity.java` 中的URL
5. Build → Build Bundle(s) / APK(s) → Build APK(s)
6. APK生成在 `app/build/outputs/apk/debug/`

---

## 方案3：Capacitor + Android Studio

如果你有Node.js和Android Studio：

```bash
# 安装Capacitor
npm init -y
npm install @capacitor/core @capacitor/cli
npx cap init "寻尤" "com.xunyou.app" --web-dir=www

# 创建Android项目
npm install @capacitor/android
npx cap add android

# 修改capacitor.config.ts中的server.url为部署地址
npx cap sync
npx cap open android  # 打开Android Studio
```

---

## APP图标

推荐使用项目中的 `static/logo.png` 作为APP图标。
可以使用 https://icon.kitchen/ 在线生成各尺寸图标。

---

## 注意事项

1. WebView APP本质是浏览器壳，需要联网才能使用
2. 首次打开可能需要加载几秒
3. 推荐开启"添加到主屏幕"功能
4. 如果聊天延迟，是PythonAnywhere免费版WebSocket限制导致
