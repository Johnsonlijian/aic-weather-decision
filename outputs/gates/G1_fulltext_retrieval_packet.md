# G1 全文检索包：四篇最近工作的获取路径与未决字段（2026-09-15）

目的：把 G1 定位矩阵中标记为 `abstract+metadata only` 的四篇高威胁最近工作，转成可复跑的获取清单，明确每篇的开放获取路径或付费墙位置、已尝试与受阻点、以及拿到全文后能消除的"不明"字段。

## 状态总览

| 工作 | DOI | 访问 | 本会话获取结果 |
|---|---|---|---|
| Døskeland, Gudmestad & Moen 2023, *Ocean Eng.* 287:115896 | 10.1016/j.oceaneng.2023.115896 | **CC-BY 开放获取**（UiS Brage 镜像 / NTNU Open） | 镜像域名 DNS 解析失败，未下载 |
| Jafarpour Hamedani & Khedmati 2024, *Ocean Eng.* (float-over topsides) | 10.1016/j.oceaneng.2024.117027 | ScienceDirect 摘要页（付费墙） | 未获取全文 |
| Tinoco, Ting & Chavan 2019, ASME OMAE2019-96137 | 10.1115/omae2019-96137 | ASME 会议论文（付费墙） | 未获取全文 |
| Zhou, Miao, Yan & Zhang 2021, *Comput. Ind. Eng.* 157:107322 | 10.1016/j.cie.2021.107322 | ScienceDirect（付费墙） | 未获取全文 |

## 逐篇获取路径与受阻点

### 1. Døskeland et al. 2023（最优先，唯一确定开放获取）
- DOI：https://doi.org/10.1016/j.oceaneng.2023.115896
- 开放获取 PDF（UiS Brage 镜像，CC-BY）：
  `https://uis.brage.unit.no/uis-xmlui/bitstream/handle/11250/3095815/1-s2.0-S0029801823022801-main.pdf?isAllowed=y&sequence=2`
- NTNU Open 记录：`https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/3101253`
- **受阻**：本会话 `uis.brage.unit.no` DNS 解析失败（curl 错误 6），`ntnuopen` 未再尝试；sciencedirect 对本机 403。
- 拿到全文后可消除的"不明"字段：是否做非预知回放、是否审计预报可用延迟、是否有决策阈值校准、是否量化 regret/unsafe 暴露。

### 2. Jafarpour Hamedani & Khedmati 2024
- DOI：https://doi.org/10.1016/j.oceaneng.2024.117027
- ScienceDirect：`https://www.sciencedirect.com/science/article/abs/pii/S0029801824003640`
- 付费墙，本会话未获授权；无确定开放获取镜像。
- 可消除字段：许可海况/作业窗定义、可作业时长、是否与基线比较、可转移性边界。

### 3. Tinoco et al. 2019
- DOI：https://doi.org/10.1115/omae2019-96137
- ASME Digital Collection 会议论文，付费墙。
- 可消除字段：集合预报如何映射为可作业窗概率、是否用真实操作回放、停机时间估计口径。

### 4. Zhou et al. 2021
- DOI：https://doi.org/10.1016/j.cie.2021.107322
- ScienceDirect 摘要页（S0360835221002266），付费墙。
- 可消除字段：时变天气过程是否用真实预报、求解器是否非预知、EDC/EDA 的具体参数与复现性。

## 结论与处置

- G1 的"可检索文献"子项已闭合（59 篇 DOI 核验、26 篇定位矩阵）；本包记录的是**升级证据等级（abstract→full text）**所需的路径。
- 本会话网络对 sciencedirect 与 uis.brage 的访问受限，全文获取属 **human-only 或需换网络环境** 的动作，不阻塞主结果。
- 在获取全文前，主稿已按保守写法处理：三篇付费墙工作只引用其标题/摘要层面的差异（"as far as the abstract shows"），不写死其方法细节为"是/否"。

## 人类待办
1. 在可访问 sciencedirect/ASME 或能解析 uis.brage 的网络环境，下载上述四篇全文。
2. 对每篇按 G1 定位矩阵的 16 列填"是/否"，替换"unclear"。
3. 若任何一篇已做"延迟审计 + 非预知回放 + 阈值校准"，需重新评估主张并可能再收紧。
