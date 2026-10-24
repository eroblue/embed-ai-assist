# 厂家 IDE GUI 烧录指南模板（vendor_flash/<标识>.md）

> **五期演进项占位模板**。`flash_tool = "vendor_ide"` 时（8 位 MCU、厂家自研 IDE
> 无 CLI），Agent 按本指南操作 IDE 完成烧录，`flash.py --collect` 收口。
> 复制本模板为 `references/vendor_flash/<project.vendor_ide 标识>.md` 后填写。

## <厂家 IDE 名称>（<标识>）

### 启动方式

- 可执行文件/`tool_paths.vendor_ide` 路径：`<填写>`
- 打开工程：`project.inputs.ide_project` 指向 `<填写 .prj/.fpk 等工程文件>`
- 需要的探针/烧录器硬件：`<填写厂家专用烧录器型号与连接方式>`

### 烧录（下载）操作步骤

1. `<填写：菜单/按钮路径，如 "工具 → 下载程序 / Download 按钮">`
2. `<填写：是否需要先选芯片型号/烧录器，配置项在哪>`
3. `<填写：确认烧录的固件路径如何填（release/ 副本绝对路径）>`

### 完成判定特征（成功）

- `<填写：输出窗口关键词，如 "Download OK" / "编程成功" / 进度条 100%>`
- `<填写：板子行为特征，如 LED 开始闪烁、串口有打印>`

### 失败输出特征

- `<填写：如 "Connect failed" / "芯片未响应" / "校验失败">`

### 注意事项

- `<填写：IDE 版本兼容性、驱动安装、烧录器固件版本要求>`
- GUI 操作由 Agent 执行时需截图确认每步状态；操作记录写入
  `outputs/s9/gui_flash_log.md`（时间 + 步骤 + 截图引用）
