# 学院通知监控（微信推送）

定时抓取学院官网通知公告，发现新通知后自动推送到你的微信。零成本、无需服务器，
代码放在 GitHub 仓库里即可 7×24 小时自动运行。

```
┌─────────────┐   定时抓取    ┌──────────┐   对比    ┌──────────┐   有新通知   ┌─────────┐
│ 学院通知页    │ ──────────► │ 解析标题/  │ ───────► │ 状态文件   │ ─────────► │ 微信推送  │
│ (党团之窗)    │              │ 链接/日期 │          │ state.json│            │(Server酱)│
└─────────────┘              └──────────┘          └──────────┘             └─────────┘
```

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `monitor.py` | 监控主脚本：抓取 → 解析 → 对比 → 推送 |
| `requirements.txt` | Python 依赖（requests、beautifulsoup4） |
| `.github/workflows/monitor.yml` | GitHub Actions 定时任务（每 2 小时一次） |
| `state.json` | 状态文件（已推送通知的记录，首次运行自动生成） |

## 第一步：获取微信推送密钥（Server酱）

1. 打开 https://sct.ftqq.com ，用微信扫码登录绑定（免费）。
2. 登录后进入"发送消息"页，复制你的 **SendKey**（一串字符，形如 `SCTxxxxxxxxxxxxxxxxxxxxxxxx`）。

## 第二步：选择运行方式

### 方式 A：GitHub Actions 云端定时（推荐，无需电脑常开）

1. 在 GitHub 新建一个仓库（公开或私有均可），把本项目文件全部上传/推送进去
   （`monitor.py`、`requirements.txt`、`.github/workflows/monitor.yml`）。
2. 仓库 **Settings → Secrets and variables → Actions → New repository secret**：
   - Name 填 `SERVERCHAN_SCKEY`
   - Secret 粘贴你的 SendKey
3. 打开 **Actions** 页面，找到"学院通知监控"，点击 **Run workflow** 手动触发一次。
4. 之后每 2 小时自动运行一次，也可以随时手动触发。

> 状态文件 `state.json` 会被自动提交回仓库，保证多轮运行之间记住"哪些已经推过"，
> 不会重复推送。

### 方式 B：自己电脑定时运行

1. 安装依赖：`pip install -r requirements.txt`
2. 设置环境变量（Windows）：`setx SERVERCHAN_SCKEY "你的SendKey"`（新开终端生效）
3. 首次运行建立基线：`python monitor.py`（脚本会自动识别首次运行，只记录不推送）
4. 添加计划任务定时运行（如每 2 小时一次）：
   ```
   schtasks /create /tn "学院通知监控" /tr "python D:\SuperFruit\学院通知监控\monitor.py" /sc HOURLY /mo 2
   ```
   （注意：电脑关机时不会运行，开机后需手动补跑一次。）

## 验证推送

改好密钥后，可以在仓库 Actions 手动触发，或本地运行 `python monitor.py`。
若提示"发现 N 条新通知"却没有收到微信，检查 SendKey 是否正确、Server酱是否已绑定微信。

## 常用操作

| 操作 | 命令 |
| --- | --- |
| 建立基线（不推送） | `python monitor.py --init` |
| 正常运行一次 | `python monitor.py` |
| 只打印不推送（未配密钥时自动） | 同上，未配置 SendKey 时仅打印清单 |

## 扩展：同时监控多个栏目/页面

学院通知可能分布在多个栏目，只需设置环境变量 `NOTICE_URLS`，多个网址用英文逗号分隔：

```
NOTICE_URLS=https://xxdt.bjfu.edu.cn/dtzc/index.html,https://xxdt.bjfu.edu.cn/其他栏目/index.html
```

本地运行时在命令前设置即可；GitHub Actions 方式请在 workflow 文件的
`env:` 段追加 `NOTICE_URLS: ${{ vars.NOTICE_URLS }}` 并在仓库 Variables 里配置。

## 注意事项

- Server酱免费版每天有推送条数限额（学院通知频率很低，完全够用）。
- 首次运行只建立基线、不推送历史通知，避免一次轰炸；之后的**新**通知才会推送。
- 推送失败的通知不会记入状态，下一次运行会自动补推。
- 学校站点 HTTPS 证书链不全，脚本已对证书校验放行（仅用于监控，不影响安全习惯）。
- 请保持合理的轮询间隔（默认每 2 小时），不要高频抓取。

## 项目亮点（面试可讲）

- 真实的**数据采集 + 监控告警 + 自动化部署**链路，而非模拟数据演示；
- 定时任务部署（GitHub Actions）、状态去重与失败重试补推等运维思维；
- 与研发运维部"系统运维与数据分析、AI 技术探索与校园场景落地"高度相关。
