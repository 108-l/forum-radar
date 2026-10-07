# 📡 24/7 全域极客情报与商业流转雷达 (Forum Intel Radar)

[![24/7 Forum Intel Radar](https://github.com/108-l/forum-radar/actions/workflows/crawl.yml/badge.svg)](https://github.com/108-l/forum-radar/actions/workflows/crawl.yml)

全天候运行在 GitHub 云端的无服务器（Serverless）多源极客情报捕获引擎。  
无需本地开机，基于 GitHub Actions 自动化定时巡检与数据持久化归档。

---

## 🌐 覆盖情报源矩阵

| 维度 / 标签 | 平台 | 接入方式 | 监控核心内容 |
| :--- | :--- | :--- | :--- |
| **🇨🇳 国内网络与车位** | **NodeSeek** | 官方 RSS 管道 | VPS 交易、特价小鸡、AI 商业车位、原生家宽 |
| **🇨🇳 独立开发与出海** | **V2EX** | 开放 JSON API | 独立产品发布、虚拟信用卡、出海变现与踩坑 |
| **🌐 全球主机英文母港** | **LowEndTalk (LET)** | 官方 RSS 管道 | 全球低价算力源头、机房倒卖、避坑测评 |
| **🇷🇺 俄区底层逆向与安全** | **Habr Infosec** | 官方 RSS 管道 | 流量混淆、底层协议逆向、AI 自动化渗透 |
| **🦞 全球邀请制系统架构** | **Lobste.rs** | 官方 RSS 管道 | 系统底层、Linux 内核、硬核架构与深度批评 |
| **🐙 全球开源爆火科技** | **GitHub Trending** | HTML 语义解析 | 每日暴涨开源黑科技武器库与实战工具 |

---

## 📂 数据归档与产物

* **`forum_archive.db`**：本地嵌入式 SQLite 数据库（WAL 事务模式），内置全量指纹去重。
* **`latest_digest.txt`**：最新一期 10 分钟全域极客情报快报卡片。
