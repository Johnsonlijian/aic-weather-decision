# GFS–KNMI 天气语义与校准探针（离线、非实证结果）

更新时间：2026-09-15

本探针把 2025 年 1 月 De Bilt（KNMI 260）的四个起报时次与 GFS `f006` 的表面 `GUST` 字段配对，共 124 个样本。配对规则固定为 `GFS valid_time == KNMI interval_end`。KNMI `FX` 表示前一小时最大风速，GFS `GUST` 表示有效时刻的格点瞬时阵风预报，因此二者只能按预先声明的时间端点做探针配对，不能解释为同一物理量的直接观测—预报误差。

通用数据剖析器给出 DQS 参考分数 81.3/100（可用但有记录限制）；该分数只是完整性、格式和重复性信号，不能证明科学有效性、独立性、代表性或投稿就绪。

## 固定分区和试验结果

拟合前按有效时刻冻结分区：训练期为 2025-01-01 至 2025-01-16，验证期为 2025-01-17 至 2025-01-23，测试期为 2025-01-24 至 2025-02-01 00:00（包含 1 月 31 日 18Z 起报的有效端点）。唯一预声明的校准器是以 `GUST_ms` 为单一自变量的 Logistic 回归；任何模型选择均不得查看测试分区。

| 目标事件 | 训练/验证/测试样本 | 状态 |
|---|---:|---|
| `KNMI FX > 11.1 m/s` | 63/28/33；阳性 7/0/4 | 仅作离线试拟合；样本短、验证期无阳性，不能报告泛化技巧 |
| `KNMI FX > 20.0 m/s` | 63/28/33；阳性 0/0/0 | 训练期单一类别，`NOT_ESTIMABLE` |

11.1 m/s 目标的试拟合参数、Brier 分数和对数损失保存在 [gfs_knmi_calibration_pilot.json](gfs_knmi_calibration_pilot.json)。这些数值只用于检查数据管线和分区代码，不能支撑天气预报性能、校准质量、施工效率或风险降低结论。

对 124 个 GRIB2 对象的 `Last-Modified` 记录审计得到相对起报时刻约 3.55–3.73 小时（中位数约 3.60 小时）。该差值只描述云归档对象的时间戳代理，不能证明同一时刻业务用户已经看到预报；逐运行明细见 [gfs_pilot_archive_timing.csv](gfs_pilot_archive_timing.csv)，其状态仍为 `NOT_ESTABLISHED`。

## 可追溯文件

- 配对表：[gfs_knmi_pilot.csv](gfs_knmi_pilot.csv)
- 配对表元数据：[gfs_knmi_pilot.metadata.json](gfs_knmi_pilot.metadata.json)
- 校准探针 JSON：[gfs_knmi_calibration_pilot.json](gfs_knmi_calibration_pilot.json)
- 归档时间戳审计：[gfs_pilot_archive_timing.csv](gfs_pilot_archive_timing.csv)、[gfs_pilot_archive_timing.metadata.json](gfs_pilot_archive_timing.metadata.json)
- 生成脚本：[build_gfs_knmi_pilot.py](../code/build_gfs_knmi_pilot.py)、[calibrate_gfs_knmi_pilot.py](../code/calibrate_gfs_knmi_pilot.py)
- 变量语义总探针：[weather_semantics_probe.json](weather_semantics_probe.json)

## 进入主实验前的门控

1. 取得可证明的业务预报发布时间或可获得时间，建立保守的信息延迟规则。
2. 增加多个预报提前量、多个季节或年份，并重新冻结训练、验证和测试分区。
3. 在测试集锁定前固定校准模型、超参数、缺测规则和行政截点分母。
4. 将校准预报与盲基线、风险感知调度在同一批天气情景和项目网络上交叉运行。
5. 保留 20 m/s 事件的不可估计状态，直到有足够的独立极端事件；不得用构造路径替代缺少的实测事件。

2026-09-15 边界校正：超限事件统一为严格大于阈值，与窗口合同中等于阈值仍可接受的规则一致。124 个样本均不等于 11.1 或 20.0 m/s，故这次语义修正不改变样本标签、分区、阳性计数或诊断分数；新增跨组件测试防止两处定义再次偏离。
