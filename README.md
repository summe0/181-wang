# 远泰社区每日安全打卡

这是一个使用 Playwright 自动完成每日安全打卡，并通过企业微信群机器人发送结果的脚本。

## GitHub Secrets

在仓库的 `Settings → Secrets and variables → Actions` 中添加：

- `CHECKIN_PASSWORD`：打卡页面登录密码
- `WECHAT_WEBHOOK`：企业微信群机器人的 Webhook 地址

账号手机号已按每家单位写入脚本；密码和 Webhook 不写入代码。

## 自动运行

工作流文件为 `.github/workflows/checkin.yml`，默认每天北京时间 08:00 运行，也可以在 Actions 页面手动运行 `daily-checkin`。

## 本地运行

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
$env:CHECKIN_PASSWORD = "你的密码"
$env:WECHAT_WEBHOOK = "你的企业微信机器人Webhook"
python daily_checkin.py
```

## 注意事项

- 不要把密码、Webhook 或 `.env` 文件提交到 GitHub。
- 每家单位之间默认等待 5 秒。
- 企业微信通知会在本次任务结束后发送成功数和失败单位列表。
