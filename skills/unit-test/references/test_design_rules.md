# S8 测试设计规则

1. 按公开接口和可观察行为划分测试单元。`unit_inventory.json` 是源码模块候选，不是准确的函数单元或主机可测性鉴定。
2. 预期结果应引用已确认需求、设计输入、接口契约或独立算法；当前实现不能充当预期依据。
3. 参数可直接传给函数时，由测试直接提供；被测代码内部调用外部接口时，才写 Mock 替代该接口。
4. 一个 `ready` 单元在 `test_plan.json` 中列出原始源文件、测试 C 文件、Mock C 文件、包含目录和每个 case 的 `scenario`、`expected`、`expected_basis`。测试代码必须在 `tests/unit/` 下。
5. 测试程序对每个 case 恰好输出一条 `S8_CASE\t<id>\tPASS/FAIL`；若有任何失败，程序应以非零码退出。运行器会拒绝缺失、重复或额外的 case。
6. 不能合理主机测试的寄存器/时序逻辑标 `not_testable_on_host`；预期不清楚标 `needs_clarification`，并说明原因。
