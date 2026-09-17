# G6 数据再分发权利审计（2026-09-15）

目的：逐项确定本研究所用第三方数据/文档能否进入公开复现包、以什么许可进入、还是只能保留本地研究区并给出获取说明。

## 结论速览

| 素材 | 许可/权利 | 能否进入公开包 | 处置 |
|---|---|---:|---|
| KNMI 逐小时观测 | **CC BY 4.0**（须署名 KNMI） | 是（派生表） | 允许再分发，派生 CSV/表格须标注来源 KNMI |
| NOAA GFS（NODD/AWS） | 公开、可任意使用；建议署名、禁止暗示 NOAA 背书 | 是（派生表 + 消息哈希清单） | 允许；再分发未改动 NOAA 数据时署名 NOAA |
| PSPLIB（J30/J60/J120） | 学术研究免费使用 | 否（原样二进制） | 仅给获取说明与实例名，不随包分发 ZIP |
| DSLIB v3.4 | 仓库无 LICENSE 文件，权利不明 | 否（原样二进制） | 仅给获取说明，不随包分发 137 MB ZIP |
| Kerkhove 2016 学位论文 / Weather-wise 作者版 PDF | 受版权保护、无再利用许可 | 否 | 本地保留，仅引用题录/URL |
| 吊车手册与规范（Yongmao、CPA TIN 101、VDOT、GB/JGJ 系列镜像） | 第三方文本/镜像 | 否（原样全文） | 仅引用条号与 URL，不重发原文/镜像 |

## 逐项依据（均 2026-09-15 核验）

1. **KNMI 逐小时观测 —— CC BY 4.0。**
   KNMI Open Data 页面（https://english.knmidata.nl/open-data）明确："The provision of these open data takes place in accordance with the CC BY 4.0 Creative Commons license, which means, among other things, that the user of the data must state that they originate from KNMI." 本研究所用的逐小时观测来自 KNMI 开放端点，属该 open data 范畴。公开派生表必须附 KNMI 署名。

2. **NOAA GFS —— NODD 公开。**
   AWS Open Data 注册页（https://registry.opendata.aws/noaa-gfs-bdp-pds/）的 License 段写明："NOAA data disseminated through NODD are open to the public and can be used as desired… NOAA requests attribution for the use or dissemination of unaltered NOAA data." 允许再分发；不得暗示 NOAA 背书；修改后不得声称为原样 NOAA 数据。本研究每消息记录 SHA-256 与字节区间，属于可复核的派生索引，可进入公开包。

3. **PSPLIB —— 学术免费。**
   PSPLIB（Kolisch & Sprecher, EJOR 1997）实例库通常以学术免费使用分发；其站点未给开放源码许可。保守处置：公开包不随附原样 ZIP，仅列出用到的 12 个 J30 实例名与获取 URL，并在 README 注明非商业学术用途。

4. **DSLIB v3.4 —— 权利不明。**
   仓库根无 LICENSE 文件（raw.githubusercontent.com/.../main/LICENSE 返回 404）。DSLIB 是对应论文的实证项目库，但未声明再分发许可。保守处置：公开包**不**包含 DSLIB 137 MB ZIP，也不把解析出的项目卡/Excel 放入派生结果；仅记录 v3.4 发布 URL 与"选择性库存"说明（本项目未把项目级数据解出到派生结果）。

5. **下载全文 —— 不进入公开包。**
   Kerkhove 2016 学位论文与 Weather-wise 作者版 PDF 均受版权保护、无再利用许可；只保留本地研究区，公开包仅含题录（DOI/URL）与"方法对照摘要"，不重发原文。

6. **规范/手册镜像 —— 仅引用，不重发。**
   Yongmao 手册、CPA TIN 101、VDOT IIM、GB/JGJ 系列（经第三方镜像）均为第三方文本或镜像；公开包只引用条号与官方/镜像 URL，不重发 PDF 或提取文本。

## 对公开复现包的影响

- **可包含**：本项目代码、派生决策表（`decision_epochs_age12.csv`，含 KNMI 派生标签与 GFS 派生预报值）、消息级 SHA-256/字节区间索引、结果 JSON、图件、README/运行手册。KNMI 派生部分须署名 KNMI；NOAA 派生部分署名 NOAA。
- **不包含**：PSPLIB/DSLIB 原始二进制、下载论文 PDF、规范/手册 PDF 或提取文本、原始 GRIB 消息。
- **人类待办（human-only）**：公开仓库创建与 push；作者确认 KNMI/NOAA 署名表述与最终许可文本。

## 状态

- KNMI、NOAA GFS 两项主数据**可再分发**（署名），故公开复现包可含派生结果。
- PSPLIB、DSLIB、下载全文、规范镜像**不随包分发**（只给获取说明与题录）。
- 因此 G6 的权利子项由"全部开放"收敛为"**主数据可再分发、其余仅可获取说明**"；投稿面要求（Highlights/CRediT/利益冲突/AI 披露/行号页码）已在主稿落实，但 live 2026 guide 仍需换环境复核。G6 保持 PARTIAL（数据权利已登记，live guide 复核 + 公开仓库仍未完成）。
