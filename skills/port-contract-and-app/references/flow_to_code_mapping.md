# 流程图到 C 代码映射规则（S5b Agent 从 Mermaid 生成/修改模块代码的唯一依据）

> 适用范围：`docs/flow/<模块>_<state|flow|sequence>.md`（**必须 status=approved**）→ 对应模块 C 代码的生成与增量修改。
> 配套：命名与文件组织见 `file_split_guide.md`；Port 接口签名见 `port_design_principle.md`。
> 硬规则：**映射必须双向可追溯**——每个状态/节点/动作在代码中有唯一可定位的对应物，traceability.json 按此登记。

## 一、命名映射总表

| 流程图元素 | 代码对应物 | 示例（模块 app_wifi） |
|---|---|---|
| 模块名（文件名段） | 源文件/头文件基名 | `app_wifi_state.md` → `app_wifi.c/.h` |
| 状态 `CONNECTED` | 枚举成员 `<模块大写>_<状态名>`，枚举类型 `<模块>_state_t` | `APP_WIFI_CONNECTED` / `app_wifi_state_t` |
| 状态机上下文 | `static` 上下文结构 `<模块>_ctx_t`（当前状态 + 模块私有数据） | `app_wifi_ctx_t` |
| 事件 `on_timeout` | 事件枚举成员 `<模块大写>_EVT_<事件名大写>`（异步事件）或直接 API 入参（同步指令） | `APP_WIFI_EVT_ON_TIMEOUT` |
| 动作 `inc_retry_counter` | `static` 函数 `<模块>_<动作名>`（动作名已含模块前缀则不重复加） | `app_wifi_inc_retry_counter()` |
| 处理节点 `A[加载配置]` | 主函数内语句块或 `static` 函数 `<模块>_<label 直译 snake_case>` | `app_wifi_load_config()` |
| 子程序节点 `A[[初始化外设]]` | 独立 `static` 函数（可跨节点复用） | `app_wifi_init_peripherals()` |
| 判断节点 `A{超时?}` | `if`/`else if` 分支（条件 = label 直译） | `if (is_timeout())` |
| 边条件 `是/否`、`len>0` | 分支条件表达式；`是`→真分支，`否`→假分支 | `if (crc_ok) {...} else {...}` |
| 时序参与者 | 层角色实例（APP/DRV/PORT/OSAL/ISR） | `app_wifi` / `uart_port` |
| 时序消息 `A->>B: f(x)` | 调用 B 层接口 `f(x)`（Port 接口签名以此为准） | `uart_port_write(...)` |
| 时序返回 `A-->>B: r` | 返回值处理 / 回调触发 | `if (ret != PORT_OK) {...}` |

## 二、状态机图 → C 代码（`<模块>_state.md` → `<模块>.c`）

标准实现骨架（switch-事件 × switch-状态 的扁平化版本，规模小用嵌套 switch，规模大用状态处理函数表）：

```c
/* app_wifi.c —— 由 app_wifi_state.md v1.0 生成（节点对应关系见注释标记） */
typedef enum {
    APP_WIFI_IDLE = 0,        /* 状态图: IDLE */
    APP_WIFI_CONNECTING,      /* 状态图: CONNECTING */
    APP_WIFI_CONNECTED,       /* 状态图: CONNECTED */
    APP_WIFI_ERROR,           /* 状态图: ERROR */
} app_wifi_state_t;

typedef struct {
    app_wifi_state_t state;
    uint8_t retry_cnt;
} app_wifi_ctx_t;

static app_wifi_ctx_t s_ctx;

/* 动作函数：与状态图 '动作' 一一对应 */
static void app_wifi_inc_retry_counter(app_wifi_ctx_t *ctx) { ctx->retry_cnt++; }

/* 事件处理：状态图迁移 (from,to,event/action) → 对应 case 的状态切换 */
void app_wifi_on_event(app_wifi_event_t ev)   /* 事件入口：公开或由轮询/回调统一分发 */
{
    switch (s_ctx.state) {
    case APP_WIFI_CONNECTING:                  /* 状态: CONNECTING */
        if (ev == APP_WIFI_EVT_ON_TIMEOUT) {   /* 迁移: CONNECTING→ERROR : on_timeout / inc_retry_counter */
            app_wifi_inc_retry_counter(&s_ctx);
            s_ctx.state = APP_WIFI_ERROR;
        } else if (ev == APP_WIFI_EVT_ON_SUCCESS) {  /* 迁移: CONNECTING→CONNECTED : on_success */
            s_ctx.state = APP_WIFI_CONNECTED;
        }
        break;
    default:
        break;
    }
}
```

映射细则：

1. **每条迁移边 → 一个条件分支**：`A --> B : evt / action` 生成"事件匹配 + 切换状态 + 前后调用动作函数"。迁移到 `[*]` → 设终态或调 deinit。
2. **动作调用时机**：标签写作 `evt / action` 时，动作在状态切换**前**执行（语义：迁移动作）。
3. **`[*] --> A` 初始迁移** → `<模块>_init()` 中 `ctx->state = <模块大写>_A;`。
4. **状态描述行**（`A : 描述`）→ 枚举成员行尾注释（不生成逻辑）。
5. **事件入口与分发**：事件来源（轮询/ISR 回调/队列）在阶段 B 顶层连接时确定，模块内只暴露 `app_wifi_on_event(ev)` 单入口。

## 三、顺序流程图 → C 代码（`<模块>_flow.md` → `<模块>.c`）

```c
/* app_boot.c —— 由 app_boot_flow.md v1.0 生成 */
int32_t app_boot_run(void)
{
    /* 节点 A[上电自检] */
    if (self_check() != 0) {          /* 判断 B{自检通过?} → 否 */
        enter_safe_mode();            /* 节点 E[进入安全模式] */
        return APP_BOOT_SAFE;         /* 节点 G((停止)) → 函数出口 */
    }
    /* 判断 B → 是 */
    load_config();                    /* 节点 C[加载配置] */
    app_boot_init_peripherals();      /* 节点 D[[初始化外设]] → 独立函数 */
    return APP_BOOT_OK;               /* 节点 F[进入主循环] 由阶段 B 接管 */
}
```

映射细则：

1. **主链节点 → 主函数体语句块**：每个节点对应一段带 `/* 节点 <id>[label] */` 注释标记的语句；节点标记注释是 diff 定位的锚，**增量修改时保留**。
2. **`[[子程序]]` 节点必须独立成函数**，调用点留在主链。
3. **判断节点 → if/else**：条件表达式直译 label；出边条件与 if/else 分支一一对应，`否`/`NG`/`else` 落到显式 else（不写裸 return 隐式分支）。
4. **有环路径**（重试回环）→ `for`/`while` + 重试计数；循环边界来自边条件里的重试上限（图上没写则补到设计输入确认，不得私自定数）。
5. **多入口/多出口**：流程图函数化后入口一个（图的单起点）；出口数 = 图中终止节点数，返回值区分各出口。

## 四、时序图 → 接口调用（`<模块>_sequence.md` → 代码 + manifest）

1. 时序图**不直接生成独立文件**，它约束两件事：
   - **Port 接口签名**：`A->>PORT: f(x)` 中的 `f` 即 Port 接口设计稿——生成 `uart_port.h` 时以时序图签名为准，同步登记进 `port_interface_manifest.json`（含调用方模块、回调方向）。
   - **模块间调用点**：`A->>B: g(x)` 在 A 模块代码中生成对 B 公开 API 的调用，调用次序按时序图纵向顺序。
2. `-->>` 返回消息 → 紧随调用的返回值检查（错误码比较 + 失败分支处理，失败分支对应图中的 alt 失败块）。
3. 回调消息（`PORT->>DRV: on_rx_data`）→ DRV 侧注册回调 + 处理函数；上下文标注（ISR/task）与 `port_design_principle.md` 第四节的回调上下文约定一致。

## 五、增量映射（diff 结果 → 代码动作）

只处理 `generation_mode=incremental` 的模块（full 全量生成、skip 不动）。每个 diff 条目按下表定点落代码：

| diff 条目 | 代码动作（**只动对应物，其余原样保留**） |
|---|---|
| 状态 added `X` | 枚举加成员 + 所属状态 case 内补分支 |
| 状态 removed | 删枚举成员 + 删对应 case + grep 确认无引用 |
| 状态 renamed `X→Y` | 枚举成员与全部引用重命名（不得保留旧名兼容别名） |
| 迁移 added | 对应 from-state 的 case 中新增事件分支 + 动作函数 |
| 迁移 removed | 删对应事件分支（动作函数无其他引用则一并删） |
| 迁移 modified（事件/动作变） | 更新该分支的事件匹配与动作调用 |
| 流程图节点 added | 主函数新增语句块（带节点标记注释）或新函数 |
| 流程图节点 removed | 删语句块/函数 + 清理调用点 |
| 流程图节点 renamed（label 变） | 更新语句块注释与函数名（label→函数名同步重命名） |
| 判断条件变（边 label 变） | 改 if 条件表达式 |
| 时序消息 added/removed | 新增/删除接口调用；**接口签名变化必须同步 manifest** |

**每变更点预期改动 ≤ 15 行**（diff_range_checker 按 3 倍阈值拦截异常重写），无关行改动必须为 0。

## 六、自检清单（生成/修改代码后）

- [ ] 每个 approved 流程图的所有节点/状态/动作在代码中有唯一对应物（注释标记在）。
- [ ] 命名映射总表逐条符合（枚举前缀、动作函数前缀、节点标记注释）。
- [ ] traceability.json 的 `flow`/`files`/`functions` 与实际产物一致。
- [ ] 时序图涉及的接口签名与 `port_interface_manifest.json` 一致。
- [ ] 增量修改后无关行零改动（跑 `diff_range_checker.py` 前自查）。
