# DSLIB 3.4 construction-network inventory

更新时间：2026-09-15

从 `DSLIB3.4.zip` 内的 `DSLIB_Analysis_Sheet.xlsx` 只读取项目元数据，按 `Sector` 不区分大小写且以 `Construction` 开头筛选，得到 163 个候选建设项目。压缩包哈希为 `19f87632c589f5d49f72b5f071992efc6379df2beb35f1efd3a60ac1381dc277`。231 个项目均有 Protrack 与 Excel 成员；项目卡成员为 228 个，其中建设子集有 2 个项目缺少项目卡成员。完整统计和每项目字段见 [dslib_construction_inventory.csv](dslib_construction_inventory.csv)，机器可读元数据见 [dslib_construction_inventory.metadata.json](dslib_construction_inventory.metadata.json)。

该库存只说明项目名称、部门分类、活动数、计划工期、预算和资源标记等元数据。它没有证明任何项目含天气敏感工序、启动/持续阈值、真实作业持续时间、预报发布时间或可复盘的现场执行记录。Protrack、项目 Excel 和项目卡均未从压缩包中解出；第三方发布包的选择性使用和再分发权利仍需核查。因此当前只能把它作为候选网络源，不能把 163 个项目写成真实天气调度实证样本。

进入主实验前需要从被选项目的原始文件中逐项确认：网络拓扑是否可解析、资源字段是否可用、活动持续时间的定义、天气敏感工序与作业合同、以及是否允许研究用途和派生数据发布。任何缺失字段都保留为缺失并在分母中记录，不以默认值补齐。
