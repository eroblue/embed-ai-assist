# Windows GUI 工具

双击 `EmbedAI-S12.exe` 配置工作流；双击 `EmbedAI-S10.exe` 采集串口日志。两者位于仓库根目录的 `tools/`，会从相邻仓库读取当前项目配置和 Skill 清单。首次启动时选择项目 `config.json`。S12 在对应 Skill 面板配置构建、烧录和串口的项目默认参数；保存方案后将执行指令复制给 Agent。

在 Windows 上重新打包：

```powershell
C:/Python314/python.exe -m pip install pyinstaller PyQt6 jsonschema pyserial
C:/Python314/python.exe tools/build_gui.py all
```

生成文件为 `tools/EmbedAI-S10.exe` 和 `tools/EmbedAI-S12.exe`。构建中间文件在 `.build/pyinstaller/`。exe 与此仓库目录一起使用；移动到其他位置后，程序无法定位仓库根配置和 Skill 清单。两个 exe 随源码提交到 Git，用户检出仓库后可直接双击使用；重新打包后应将更新的 exe 一起提交。
