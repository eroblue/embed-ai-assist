# J-Flash CLI 自动化模式指南（二期演进项）

> **本指南为演进期占位**——`flash_tool = "jflash"` 当前在本版 prepare 直接报错
> （一期仅支持 jlink 全链路）。二期实装时按本骨架补全并实测校准。

## 定位

- 可执行文件：`JFlash.exe`（`tool_paths.jflash`，无推导、缺失报错；本键兼作
  jlink 的 SEGGER 安装目录探测线索）
- 适用场景：需要 J-Flash 工程级烧录配置（外部 Flash 映射、多区域布局、生产烧录
  序列）的场合；日常开发烧录用 `jlink`（J-Link Commander）更直接

## .jflash 工程文件决策流程（二期实装）

搜索顺序：`--jflash-project` 参数 > `project.flash_config` 配置项 >
`release/*.jflash` 约定（多份 → 退出码 2 列出候选）。
未找到 → prepare 退出码 3，Agent 转达用户决策：

- **自提供**：用户将 `.jflash` 放入 `release/` 或配置 `flash_config` 后重跑 S9
  （非错误，state 保持 pending）
- **自动生成**：`prepare.py --gen-jflash` → 按设备名映射链/`--interface`/
  Flash 基址与容量（复用 S7b 来源链）生成 `release/flash.jflash`（INI 文本，
  带生成标记），**生成后不覆盖**（含用户修改；设备名不符仅警告）

## 命令预告（二期实测校准）

```
JFlash.exe -openprj <release/flash.jflash> -open <固件> -auto -start -exit
```

成功/失败日志特征待二期补充至 flash_log_parse_rules.md。
