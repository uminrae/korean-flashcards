; =====================================================================
;   未来的韩语卡片 - Inno Setup 7 简体中文专业安装向导配置脚本
; =====================================================================

#define MyAppName "未来的韩语卡片"
#define MyAppVersion "1.1"
#define MyAppPublisher "未来的韩语卡片工作室"
#define MyAppURL "https://github.com"
#define MyAppExeName "未来的韩语卡片.exe"
#define MyAppIcoName "app_icon.ico"

[Setup]
; 唯一识别 GUID
AppId={{5E4F8B32-9A1C-4E82-94C3-B245D8C1A88B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 默认安装路径: C:\Program Files\KoreanFlashcards
DefaultDirName={autopf}\KoreanFlashcards
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; 输出目录与安装包名称
OutputDir=Output
OutputBaseFilename=未来的韩语卡片_Setup_v{#MyAppVersion}
SetupIconFile=assets\{#MyAppIcoName}
UninstallDisplayIcon={app}\{#MyAppExeName},0

; 极致高压缩比配置 (LZMA2 Solid 算法)
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=auto
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
; 优先使用编译器自带中文语言包，同时备选当前目录下的 ChineseSimplified.isl 保证 100% 独立便携
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl,ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(&D)"; GroupDescription: "附加快捷方式:"; Flags: checkedonce
Name: "autostart"; Description: "开机自动启动(&B)"; GroupDescription: "系统设置:"; Flags: unchecked

[Files]
; 1. 显式将高清图标复制到 {app}\assets\ 与 {app}\ 根目录，确保快捷方式绝对能精准寻址图标
Source: "assets\{#MyAppIcoName}"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\{#MyAppIcoName}"; DestDir: "{app}"; Flags: ignoreversion
; 2. 挂载 PyInstaller 生成的 dist/ 完整目录结构与动态库
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 桌面快捷方式 (强制指定 {app}\assets\app_icon.ico 专属高清图标源)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\{#MyAppIcoName}"; Tasks: desktopicon

; 开始菜单快捷方式组与一键卸载项
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\{#MyAppIcoName}"
Name: "{autoprograms}\{#MyAppName}\卸载{#MyAppName}"; Filename: "{uninstallexe}"

[Registry]
; 开机自启动注册表项关联（当用户勾选开机启动时写入，卸载时自动清理）
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FutureKoreanCards"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; 安装向导尾页启动程序提示（默认勾选）
Filename: "{app}\{#MyAppExeName}"; Description: "运行 未来的韩语卡片(&L)"; Flags: nowait postinstall skipifsilent
