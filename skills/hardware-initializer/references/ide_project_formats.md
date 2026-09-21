# IDE 项目文件格式说明

S5a/S5b/S5c 生成代码后，由公共工具 `skills/_shared/scripts/ide_sync.py` 将源文件同步进 IDE 项目文件（各 Skill validate 段自动调用，也可手动运行）。本文件记录各格式要点。

## Keil MDK（.uvprojx）

XML 结构，关键节点：

```xml
<Project>
  <Targets>
    <Target>
      <TargetOption>...</TargetOption>   <!-- 编译选项/宏/include 路径 -->
      <Groups>
        <Group>
          <GroupName>Drivers/BSP</GroupName>
          <Files>
            <File>
              <FileName>clock_init.c</FileName>
              <FileType>1</FileType>      <!-- 1=C 源文件, 2=头文件 -->
              <FilePath>..\Drivers\BSP\Src\clock_init.c</FilePath>
            </File>
          </Files>
        </Group>
      </Groups>
    </Target>
  </Targets>
</Project>
```

- include 路径在 `<IncludePath>` 文本节点，分号分隔：`..\Drivers\BSP\Inc;..\Drivers\Port\Inc`
- 更新时保留原工程配置（编译选项、宏、其他 Group）
- 优先按 `GroupName` 查找已有分组，复用而非新建

## IAR EWARM（.ewp）

XML 结构，`<group><name>init</name><files><file><name>...</name></file></files></group>`，
路径相对 `.ewp` 文件（通常带 `$PROJ_DIR$` 前缀）。公共工具 ide_sync.py 支持 Keil 与
IAR 两种格式的自动同步（IAR 的 include 路径在 `CCIncludePath2` option 的 `<state>` 子元素）。

## STM32CubeIDE（.project / .cproject）

Eclipse 工程：`.project` 记录 natures/buildSpec，`.cproject` 记录 include 路径与源码目录。
源码目录下的 .c 自动参与编译（无需逐文件注册），只需保证 include 路径正确。

## 项目文件缺失时

公共工具不自动创建工程，输出 `outputs/_shared/ide_sync_manual.md` 手动同步清单（相对目标工程根），内容包括：失败原因、按 group 分组的待添加源文件、待添加 include 路径、Keil/IAR 操作指引。

用户手动创建工程（保存到 `<项目根>/<目标工程>/` 下的 IDE 工程目录——32 位为 `MDK-ARM/` / `IAR/`，8 位为 `Project/`，见 `docs/PROJECT_LAYOUT.md`）后，重新运行即可自动同步：

```bash
python skills/_shared/scripts/ide_sync.py --project <项目根> --target <App|BootLoader> --ide keil
```

## 工具链路径

全局 `config.json` 的 `tool_paths.keil` 指定 UV4.exe，可用于命令行编译验证
（S5 编译烧录验证环节使用）。
