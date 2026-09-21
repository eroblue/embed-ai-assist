# 低功耗策略参考（S5a Agent 决策依据）

用户仅声明 `project.power.enabled = true`，具体策略由 Agent 综合以下材料自主决策，
**不暴露给用户配置**：唤醒源、模式选择、Tickless 等。

## 决策输入

| 材料 | 用途 |
|---|---|
| S3 寄存器/SVD | 低功耗寄存器位定义（PMU/PWR/SCB_SCR） |
| S3 datasheet | 各模式电流、唤醒时间 |
| S3 clock_tree | 可关断时钟域 |
| S4 circuit facts | 实际接了哪些唤醒引脚（WKUP/PA0/EXTI） |
| S2 功能需求 | 何时该睡、什么事件必须唤醒 |
| 厂商 demo / 联网搜索 | 官方推荐写法、已知坑 |

## 模式选择规则（经验值）

| 需求特征 | 建议模式 |
|---|---|
| RAM/寄存器保持 + 快速唤醒（<1μs） | Sleep（WFI） |
| 中等省电 + RTC 保持 | Deep-Sleep（GD32 PMU_DEEPSLEEP / STM32 STOP） |
| 最低功耗 + 唤醒后复位重启 | Standby（STM32）/ Deep-sleep + 全关（GD32） |
| RTOS 空闲即睡 | Tickless Idle（SysTick 抑制 + 定时补偿） |

## 平台要点

### GD32F20x
- 进入：`pmu_to_deepsleepmode(PMU_LDO_NORMAL, WFI_CMD, PMU_DEEPSLEEP)`
- 唤醒后 HXTAL/PLL 停振，须重走 `clock_init()` 时钟恢复路径
- 备份域访问前需 `pmu_backup_write_enable()`
- 低功耗时钟源确认 LXTAL/IRC40K（S4 facts 的 32.768kHz 晶振即 LXTAL）

### STM32F103
- 进入：`PWR_EnterSTOPMode(PWR_Regulator_LowPower, PWR_STOPEntry_WFI)`
- STOP 唤醒后 HSI 8MHz 接管，须重配 SYSCLK
- WKUP 引脚仅 PA0（S4 若发现 PA0-WKUP 网络即候选唤醒源）
- 待机模式 WKUP 上升沿唤醒，唤醒等效复位

## 生成物约束

- `flat`：低功耗逻辑内联 `board_init.c/h`，不生成 `power_port.h`
- `layered/full`：生成 `Drivers/BSP/{Src,Inc}/power_init.c/h` + capabilities.power 段；
  Port 接口由 S5b 定义、S5c 实现
- RTOS 场景：tickless 由 S5c 的 `port_impl_osal_<rtos>.c` 对接 idle hook
