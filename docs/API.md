# 捷途汽车 App API 接口文档

## 基础信息

| 项目 | 值 |
|------|-----|
| **App 名称** | com.jetour.traveller (捷途Traveller) |
| **版本** | 3.2.77 (versionCode: 26033101) |
| **登录域名** | `https://uaa-consumer.jetour.com.cn/` |
| **业务域名** | `https://mobile-consumer.jetour.com.cn/` |

---

## 一、登录 API

### 1. 发送短信验证码

```
POST /api/v1/common/mobile/sms
Host: uaa-consumer.jetour.com.cn
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `mobile` | String | 是 | 手机号 |
| `smsType` | String | 是 | 短信类型 (login/register/forgot) |
| `captchaVerification` | String | 否 | 防水验证码票据 |

**响应示例：**

```json
{
  "status": 200,
  "error": "maskit.success.general",
  "message": "Success",
  "data": true
}
```

---

### 2. 验证码登录

```
POST /api/v1/uaa/mobile/mobile-code-login
Host: uaa-consumer.jetour.com.cn
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `mobile` | String | 是 | 手机号 |
| `smsCode` | String | 是 | 短信验证码 |
| `smsType` | String | 是 | 短信类型 (login) |
| `inviteCode` | String | 否 | 邀请码 |
| `deviceId` | String | 否 | 设备ID |

**响应示例：**

```json
{
  "status": 200,
  "data": {
    "accessToken": "xxx",
    "refreshToken": "xxx",
    "userId": "xxx"
  }
}
```

---

### 3. 一键登录

```
POST /api/v1/uaa/mobile/one-click
Host: uaa-consumer.jetour.com.cn
Content-Type: application/json
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `accessToken` | String | 是 | 运营商授权token |
| `deviceId` | String | 是 | 设备ID |

---

### 4. 第三方登录

| 平台 | 登录 URL |
|------|---------|
| 微信 | `POST /api/v1/thirdparty/wechat/login` |
| Apple | `POST /api/v1/thirdparty/apple/login` |
| 微博 | `POST /api/v1/thirdparty/weibo/login` |

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `code` | String | 是 | 授权code |
| `inviteCode` | String | 否 | 邀请码 |

---

## 二、签到 API

### 1. 获取签到任务信息

```
GET /web/task/tasks/load-one?sceneCode=signInScene&terminal=4&access_token=xxx
Host: mobile-consumer.jetour.com.cn
```

**响应示例：**

```json
{
  "status": 200,
  "data": {
    "taskId": "3439799346990943525",
    "taskName": "签到",
    "taskStatus": 1
  }
}
```

---

### 2. 签到页面信息

```
GET /web/task/sign/sign-page?sceneCode=signInScene&taskId=xxx&access_token=xxx
Host: mobile-consumer.jetour.com.cn
```

**响应示例：**

```json
{
  "status": 200,
  "data": {
    "pointReward": 1,
    "memberReward": 0,
    "cycleType": 2,
    "cycleDays": 1,
    "distanceNext": 6
  }
}
```

---

### 3. 执行签到（加密）

```
POST /web/task/tasks/event-start?encryptParam=xxx
Host: mobile-consumer.jetour.com.cn
encryptFlag: true
riskParam: {"slideParam":"","decisionData":""}
volcParam: {"devToken":"xxx","appVersion":"3.2.83",...}
Content-Type: application/json
```

**请求体（加密）：**

```
gXH4rVw42PRhIfeubA3AaElTOzFQx6onNgBn11yuHwRPCvIIi3YL4V4aEsfB5kUq
```

---

### 4. 签到记录

```
GET /web/task/sign/sign-record?taskId=xxx&monthInYear=202602&access_token=xxx
Host: mobile-consumer.jetour.com.cn
```

---

## 三、盲盒 API

### 1. 盲盒列表

```
GET /web/rights/blind-box/user/paging?access_token=xxx
Host: mobile-consumer.jetour.com.cn
```

**响应示例：**

```json
{
  "status": 200,
  "data": {
    "total": 173,
    "data": [{
      "id": "6250377670062237834",
      "boxName": "2月惊喜盲盒",
      "pointNum": 0
    }]
  }
}
```

---

### 2. 盲盒数量

```
GET /web/rights/blind-box/user/count?access_token=xxx
Host: mobile-consumer.jetour.com.cn
```

---

### 3. 领取盲盒（加密）

```
POST /web/rights/blind-box/receive?businessCode=xxx&accountId=xxx&access_token=xxx
Host: mobile-consumer.jetour.com.cn
```

---

## 四、用户信息 API

### 1. 当前用户信息

```
GET /web/user/current?access_token=xxx
Host: mobile-consumer.jetour.com.cn
```

---

### 2. 积分流水

```
GET /web/point/flow?access_token=xxx&pageNo=1&pageSize=10
Host: mobile-consumer.jetour.com.cn
```

---

## 五、加密参数说明

### encryptParam

URL 查询参数，Base64 编码的加密数据。

### encryptFlag

固定值 `true`，表示请求已加密。

### riskParam

```json
{
  "slideParam": "",
  "decisionData": ""
}
```

### volcParam

```json
{
  "devToken": "设备Token",
  "appVersion": "3.2.83",
  "devicePlatform": "ios",
  "deviceBrand": "iPhone17,1",
  "osVersion": "26.1"
}
```

---

## 六、请求头

| Header | 值 |
|--------|-----|
| `Content-Type` | `application/json;charset=UTF-8` |
| `account` | `gh_aafc4b079157` (微信小程序) |
| `User-Agent` | 微信小程序 UA 或 App UA |
| `Origin` | `https://h5-app.jetour.com.cn` |