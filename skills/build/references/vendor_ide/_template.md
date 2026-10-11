# 厂家 IDE GUI 编译指南编写模板

> 用途：`build_system = "vendor_ide"` 时，prepare 按 `project.vendor_ide` 定位
> `references/vendor_ide/<标识>.md`。**指南不存在则 prepare 报错**——为新的
> 厂家 IDE 接入时，复制本模板为 `<标识>.md` 并填充全部小节（如
> `fmd_ft.md` 对应辉芒微 FT 平台）。

## 必须覆盖的六个小节

```markdown
# <厂家 IDE 名>（vendor 标识：<id>）GUI 编译指南

## 1. IDE 启动方式
- 可执行文件：tool_paths.vendor_ide（config 全局层配置）
- 启动参数（如支持命令行打开工程）：<参数模板>；不支持时说明手工打开路径

## 2. 打开工程
- 菜单路径 / 启动参数如何加载 project.inputs.ide_project
- IDE 就绪的窗口特征（如状态栏就绪 / 工程树出现 target 节点）

## 3. 编译快捷键（仅限本节列出的操作）
- 快捷键：<如 F7 / Ctrl+F7>；菜单路径：<如 Project → Build All>
- **Rebuild 与 Build 的区分**（如有）

## 4. 输出目录约定
- 编译输出目录相对工程根的默认路径（config 缺省值，如 Project/Output/）
- 产物命名规则（<name>.hex / <name>.bin）

## 5. 编译完成判定特征
- 输出窗口完成特征（如 "Build succeeded" / "0 Error(s)"）
- 编译失败特征（如 "Error:" / 弹窗）；弹窗处置（只读错误信息后关闭）

## 6. 常见错误输出窗口特征
- 编译错误 / 链接错误 / 环境错误（如 License 弹窗）各自的表现
```

## 编写红线

- 只登记**确定存在**的快捷键与菜单路径（以该 IDE 实际版本验证为准）
- 不得包含"打开工程配置对话框"类操作——S7b 禁止修改工程文件
- 超时、产物 mtime 判定、不保存工程改动等通用规则由任务书统一给出，指南不重复
