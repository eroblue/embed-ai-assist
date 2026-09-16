# 原理图引脚表 Excel 输出格式规范

参考样例：`原理图网络表.png`（GD32F205VET 引脚配置表）。

## 文件位置

- 输出路径：`outputs/pin_table.xlsx`
- 数据来源：`outputs/circuit_netlist.json`（由 parse.py 解析原理图生成）

## 工作表（Sheet）结构

所有元件放在**同一个工作表**（命名 `引脚配置`），便于通读和筛选。
每个元件一个**区块**，自上而下依次排列：

```
C1（0.1uF）— 2 引脚          ← 元件标题行（合并 A:C 单元格，蓝底加粗）
引脚号 | 引脚名 | 网络名      ← 表头行（深蓝底白字）
1      | 1      | VCC
2      | 2      | GND
                              ← 空行分隔
C2（0.1uF）— 2 引脚
...
```

元件区块按网表中元件顺序排列。

## 列定义

| 列 | 表头 | 数据来源 | 说明 |
|----|------|---------|------|
| A | 引脚号 | netlist `components[].pins[].pin` | 元件引脚编号 |
| B | 引脚名 | netlist `components[].pins[].pin_name` | 如 PA0、VBAT |
| C | 网络名 | netlist `components[].pins[].net` | 悬空引脚显示"未连接" |

表头样式：蓝底白字加粗。

> 说明：「作用 / 外设/模式」两列已删除——引脚功能角色的判断归
> S4 circuit-investigator（产物 `outputs/circuit_facts.xlsx`），
> 引脚级精确复用映射（如 PA9 = USART1_TX）需 datasheet 引脚复用表，
> 由 S3 datasheet-extractor + S4 circuit-investigator 完成深度标注。

## 行颜色编码

参考样例图的视觉分组规则：

| 行类别 | 填充色 | 说明 |
|--------|--------|------|
| 电源引脚 | 蓝色 `D9E1F2` | VDD/VSS/VBAT 等 |
| 特殊功能引脚 | 黄色 `FFF2CC` | SWD / BOOT / NRST / 晶振 |
| 悬空引脚 | 灰色 `E7E6E6` | 未连接任何网络 |
| 普通引脚 | 白色（无填充） | GPIO / 外设引脚 |

## 依赖

- Python 库：`openpyxl`（缺失时 parse.py 记录警告并跳过 Excel 导出，不影响网表主流程）
