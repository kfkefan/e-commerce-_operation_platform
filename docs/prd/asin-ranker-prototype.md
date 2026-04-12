# ASIN 关键词排名追踪器 - 原型图

## 1. 用户界面布局

### 1.1 主界面整体布局

```mermaid
block-beta
columns 1
  header["🔍 ASIN 关键词排名追踪器"]
  block:main:3
    columns 3
    block:inputSection:1
      columns 1
      asinLabel["ASIN 输入"]
      asinInput["B0XXXXXXXX"]
      kwLabel["关键词列表（每行一个）"]
      kwInput["关键词 1\n关键词 2\n关键词 3\n..."]
      pageLabel["最大翻页数"]
      pageInput["5 (1-50)"]
    end
    block:controlSection:1
      columns 1
      space
      startBtn["🚀 开始追踪"]
      pauseBtn["⏸️ 暂停"]
      exportBtn["📥 导出 Excel"]
      historyBtn["📜 历史记录"]
      space
    end
    block:statusSection:1
      columns 1
      progressLabel["任务进度"]
      progressBar["████████░░ 50%"]
      stat1["已处理：25/50"]
      stat2["剩余时间：~2 分钟"]
      stat3["状态：运行中"]
    end
  end
  block:result:3
    columns 1
    resultTitle["📊 排名结果"]
    filterBar["🔍 搜索 | 筛选：全部 ▼ | 排序：关键词 ▲"]
    resultTable["结果表格区域"]
  end
  footer["状态栏 | 最后更新：2026-04-11 21:23 | 共 50 条记录"]
```

### 1.2 输入区域详细布局

```mermaid
block-beta
columns 2
  block:left:1
    columns 1
    block1["┌─────────────────────────────────┐"]
    block2["│ 🔑 ASIN 输入                    │"]
    block3["│ ┌───────────────────────────┐   │"]
    block4["│ │ B08N5WRWNW                │   │"]
    block5["│ └───────────────────────────┘   │"]
    block6["│ ✓ 格式正确                      │"]
    block7["└─────────────────────────────────┘"]
  end
  block:right:1
    columns 1
    blockA["┌─────────────────────────────────┐"]
    blockB["│ 📝 最大翻页数配置               │"]
    blockC["│ ┌─────────┐                     │"]
    blockD["│ │    5    │ ← 滑动或输入 1-50   │"]
    blockE["│ └─────────┘                     │"]
    blockF["│ ⏱️ 预估时间：~5 分钟            │"]
    blockG["└─────────────────────────────────┘"]
  end
  space
  block:kw:2
    columns 1
    blockH["┌─────────────────────────────────────────────┐"]
    blockI["│ 📋 关键词列表 (已输入 15 个，最多 100 个)       │"]
    blockJ["│ ┌───────────────────────────────────────┐   │"]
    blockK["│ │ wireless earbuds                      │   │"]
    blockL["│ │ bluetooth headphones                  │   │"]
    blockM["│ │ noise cancelling earbuds              │   │"]
    blockN["│ │ sports earphones                      │   │"]
    blockO["│ │ ... (滚动查看更多)                    │   │"]
    blockP["│ └───────────────────────────────────────┘   │"]
    blockQ["│ 💡 提示：可从 Excel 直接复制粘贴            │"]
    blockR["└─────────────────────────────────────────────┘"]
  end
```

### 1.3 结果表格布局

```mermaid
block-beta
columns 1
  toolbar["┌─────────────────────────────────────────────────────────────────┐"]
  toolbar2["│ 🔍 搜索关键词  [筛选：全部 ▼]  [排序：自然排名 ▲]  [📥 导出]    │"]
  toolbar3["└─────────────────────────────────────────────────────────────────┘"]
  table["┌──────┬────────────────────┬───────────┬───────────┬────────┐"]
  table2["│ #    │ 关键词             │ 自然排名  │ 广告排名  │ 状态   │"]
  table3["├──────┼────────────────────┼───────────┼───────────┼────────┤"]
  table4["│ 1    │ wireless earbuds   │ P1-#3     │ P1-#1     │ ✅     │"]
  table5["│ 2    │ bluetooth headphones│ P2-#5    │ -         │ 🟡     │"]
  table6["│ 3    │ noise cancelling   │ -         │ P1-#2     │ 🟠     │"]
  table7["│ 4    │ sports earphones   │ 未收录    │ 未收录    │ ❌     │"]
  table8["│ ...  │ ...                │ ...       │ ...       │ ...    │"]
  table9["└──────┴────────────────────┴───────────┴───────────┴────────┘"]
  pagination["← 上一页  1/5  下一页 →  |  每页显示：20 ▼  |  共 98 条记录"]
```

---

## 2. 交互流程图

### 2.1 完整用户操作流程

```mermaid
flowchart TD
    Start([用户打开应用]) --> InputPage[输入页面]
    
    InputPage --> Validate{输入验证}
    Validate -->|ASIN 格式错误 | ShowError1[显示错误提示]
    ShowError1 --> InputPage
    Validate -->|关键词为空 | ShowError2[提示至少输入 1 个关键词]
    ShowError2 --> InputPage
    Validate -->|翻页数超限 | AutoFix[自动修正为边界值]
    AutoFix --> InputPage
    Validate -->|验证通过 | ConfirmPage[确认页面]
    
    ConfirmPage --> ShowSummary[显示任务摘要]
    ShowSummary --> UserConfirm{用户确认？}
    UserConfirm -->|取消 | InputPage
    UserConfirm -->|开始 | TaskRunning[任务执行中]
    
    TaskRunning --> ShowProgress[显示实时进度]
    ShowProgress --> CheckStatus{任务状态}
    CheckStatus -->|运行中 | UpdateProgress[更新进度条]
    UpdateProgress --> ShowProgress
    CheckStatus -->|用户暂停 | TaskPaused[任务暂停]
    CheckStatus -->|遇到验证码 | CaptchaAlert[提示手动验证]
    CheckStatus -->|完成 | ResultPage[结果页面]
    
    TaskPaused --> ResumeOption{继续或取消？}
    ResumeOption -->|继续 | TaskRunning
    ResumeOption -->|取消 | InputPage
    
    CaptchaAlert --> UserSolve[用户解决验证码]
    UserSolve --> TaskRunning
    
    ResultPage --> ViewResult[查看排名表格]
    ViewResult --> UserAction{用户操作}
    
    UserAction -->|排序 | SortTable[表格排序]
    UserAction -->|筛选 | FilterTable[表格筛选]
    UserAction -->|导出 | ExportFile[导出 Excel/CSV]
    UserAction -->|新任务 | InputPage
    
    SortTable --> ViewResult
    FilterTable --> ViewResult
    ExportFile --> SaveSuccess[保存成功提示]
    SaveSuccess --> ViewResult
```

### 2.2 数据爬取流程

```mermaid
flowchart TD
    StartTask[开始任务] --> GetKeywordList[获取关键词列表]
    GetKeywordList --> InitCounter[初始化计数器 i=0]
    
    InitCounter --> CheckLimit{i < 总数？}
    CheckLimit -->|否 | TaskComplete[任务完成]
    CheckLimit -->|是 | GetKeyword[获取第 i 个关键词]
    
    GetKeyword --> BuildURL[构建亚马逊搜索 URL]
    BuildURL --> SendRequest[发送 HTTP 请求]
    SendRequest --> CheckResponse{响应状态}
    
    CheckResponse -->|超时 | Retry{重试次数<3?}
    Retry -->|是 | WaitRetry[等待后重试]
    WaitRetry --> SendRequest
    Retry -->|否 | MarkTimeout[标记为超时]
    MarkTimeout --> NextKeyword
    
    CheckResponse -->|验证码 | PauseCaptcha[暂停并提示用户]
    PauseCaptcha --> UserVerify[用户验证]
    UserVerify --> SendRequest
    
    CheckResponse -->|成功 | ParseHTML[解析 HTML]
    ParseHTML --> FindASIN{找到 ASIN?}
    
    FindASIN -->|否 | CheckMorePage{还有下一页？}
    CheckMorePage -->|是 | IncPage[页码 +1]
    IncPage --> CheckPageLimit{超过最大页数？}
    CheckPageLimit -->|否 | BuildURL
    CheckPageLimit -->|是 | MarkNotFound[标记未收录]
    CheckMorePage -->|否 | MarkNotFound
    
    FindASIN -->|是 | ExtractPos[提取位置信息]
    ExtractPos --> CheckType{自然 or 广告？}
    CheckType -->|自然 | SaveOrganic[保存自然排名]
    CheckType -->|广告 | SaveAd[保存广告排名]
    
    SaveOrganic --> CheckBoth{两者都找到？}
    SaveAd --> CheckBoth
    CheckBoth -->|否 | CheckMorePage
    CheckBoth -->|是 | SaveResult[保存完整结果]
    
    SaveResult --> NextKeyword[下一个关键词 i++]
    NextKeyword --> CheckLimit
    
    TaskComplete --> GenerateReport[生成结果报告]
    GenerateReport --> EndTask([任务结束])
```

### 2.3 状态机图

```mermaid
stateDiagram-v2
    [*] --> Idle: 应用启动
    
    Idle --> Inputting: 用户开始输入
    Inputting --> Validating: 点击开始按钮
    Validating --> Inputting: 验证失败
    Validating --> Confirming: 验证通过
    Confirming --> Inputting: 用户取消
    Confirming --> Running: 用户确认
    
    Running --> Paused: 用户点击暂停
    Running --> CaptchaWait: 遇到验证码
    Running --> Completed: 所有关键词处理完毕
    Running --> Failed: 发生严重错误
    
    Paused --> Running: 用户点击继续
    Paused --> Idle: 用户取消任务
    
    CaptchaWait --> Running: 用户完成验证
    CaptchaWait --> Paused: 用户选择稍后
    
    Completed --> Viewing: 查看结果
    Viewing --> Exporting: 点击导出
    Viewing --> Idle: 开始新任务
    
    Exporting --> Viewing: 导出完成
    
    Failed --> Idle: 关闭错误提示
    Failed --> Running: 重试任务
    
    note right of Running
        显示实时进度
        可暂停/继续
        预计剩余时间
    end note
    
    note right of Viewing
        支持排序/筛选
        支持导出
        支持复制数据
    end note
```

---

## 3. 关键界面状态

### 3.1 空状态（无数据时）

```mermaid
block-beta
columns 1
  emptyBox["┌─────────────────────────────────────┐"]
  emptyIcon["│           📊                      │"]
  emptyText1["│     暂无排名数据                  │"]
  emptyText2["│  输入 ASIN 和关键词后开始追踪      │"]
  emptyBtn["│     [🚀 开始第一个任务]            │"]
  emptyBottom["└─────────────────────────────────────┘"]
```

### 3.2 加载中状态

```mermaid
block-beta
columns 1
  loadBox["┌─────────────────────────────────────┐"]
  loadAnim["│         ⏳ 正在处理关键词...        │"]
  loadBar["│   ████████░░░░░░░░  50% (25/50)    │"]
  loadDetail["│  当前：wireless earbuds          │"]
  loadTime["│  剩余时间：约 2 分钟                │"]
  loadBtn["│         [⏸️ 暂停]                  │"]
  loadBottom["└─────────────────────────────────────┘"]
```

### 3.3 错误状态

```mermaid
block-beta
columns 1
  errBox["┌─────────────────────────────────────┐"]
  errIcon["│           ⚠️                      │"]
  errTitle["│        任务执行失败               │"]
  errMsg["│  原因：网络连接超时                 │"]
  errSuggest["│  建议：检查网络后重试            │"]
  errBtn1["│  [🔄 重试]     [📋 查看日志]      │"]
  errBtn2["│           [❌ 关闭]                │"]
  errBottom["└─────────────────────────────────────┘"]
```

---

## 4. 响应式布局说明

### 4.1 桌面端（≥1200px）

```
┌─────────────────────────────────────────────────────────┐
│  Header (Logo + 标题)                                    │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │             │  │             │  │             │     │
│  │  ASIN 输入   │  │  控制按钮   │  │  任务状态   │     │
│  │             │  │             │  │             │     │
│  │  关键词列表  │  │  开始/暂停  │  │  进度条     │     │
│  │             │  │             │  │             │     │
│  │  翻页配置   │  │  导出/历史  │  │  统计信息   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
├─────────────────────────────────────────────────────────┤
│  结果表格区域（全宽）                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 工具栏 + 表格 + 分页                              │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 平板端（768px - 1199px）

```
┌─────────────────────────────────────┐
│  Header                              │
├─────────────────────────────────────┤
│  ┌───────────────┐ ┌───────────────┐│
│  │  ASIN 输入     │ │  控制按钮     ││
│  │  关键词列表   │ │  任务状态     ││
│  │  翻页配置     │ │  进度条       ││
│  └───────────────┘ └───────────────┘│
├─────────────────────────────────────┤
│  结果表格区域（可横向滚动）            │
└─────────────────────────────────────┘
```

### 4.3 移动端（<768px）

```
┌─────────────────────┐
│  Header             │
├─────────────────────┤
│  ASIN 输入          │
├─────────────────────┤
│  关键词列表         │
├─────────────────────┤
│  翻页配置           │
├─────────────────────┤
│  开始按钮           │
├─────────────────────┤
│  任务状态/进度      │
├─────────────────────┤
│  结果表格           │
│  (简化列，可滑动)   │
└─────────────────────┘
```

---

## 5. 组件交互细节

### 5.1 关键词输入框

```mermaid
sequenceDiagram
    participant U as 用户
    participant I as 输入框
    participant V as 验证器
    participant C as 计数器
    
    U->>I: 粘贴多行文本
    I->>V: 触发验证
    V->>V: 分割行、去重、过滤空行
    V->>C: 更新计数
    C-->>I: 显示"已输入 X 个"
    I-->>U: 实时更新显示
    
    U->>I: 输入超过 100 行
    I->>V: 触发验证
    V->>V: 截取前 100 行
    V-->>I: 返回截断后数据
    I-->>U: 提示"已自动截取前 100 个关键词"
```

### 5.2 进度条更新

```mermaid
sequenceDiagram
    participant T as 任务执行器
    participant P as 进度条组件
    participant S as 状态显示
    participant U as 用户界面
    
    loop 每个关键词处理
        T->>P: 更新进度值 (current/total)
        P->>P: 计算百分比
        P->>S: 更新文本显示
        S->>U: 渲染新状态
        T->>S: 更新预计剩余时间
        S->>U: 更新时间显示
    end
    
    T->>P: 进度 100%
    P->>U: 显示完成动画
    T->>S: 显示"完成！"
```

---

## 6. 数据流向图

```mermaid
flowchart LR
    subgraph 用户输入
        UI[用户界面]
        ASIN[ASIN 输入]
        KW[关键词列表]
        PG[翻页数]
    end
    
    subgraph 数据处理
        VAL[验证模块]
        QUEUE[任务队列]
        SCHED[调度器]
    end
    
    subgraph 爬取引擎
        REQ[请求发送]
        PARSE[HTML 解析]
        EXTR[数据提取]
    end
    
    subgraph 存储展示
        STORE[本地存储]
        TABLE[结果表格]
        EXPORT[导出模块]
    end
    
    UI --> ASIN
    UI --> KW
    UI --> PG
    
    ASIN --> VAL
    KW --> VAL
    PG --> VAL
    
    VAL --> QUEUE
    QUEUE --> SCHED
    SCHED --> REQ
    REQ --> PARSE
    PARSE --> EXTR
    EXTR --> STORE
    STORE --> TABLE
    TABLE --> EXPORT
    
    EXPORT -.->|CSV/Excel | UI
```

---

*原型图文档结束*
