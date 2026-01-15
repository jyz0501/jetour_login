# 捷途签到信息自动提取与展示系统

## 功能介绍

本项目是一个自动提取并展示捷途每日签到信息的系统，主要功能包括：

1. **自动提取签到数据**：通过 GitHub Actions 每日自动从捷途 API 提取签到记录
2. **实时统计分析**：计算签到率、连续签到天数等统计数据
3. **可视化展示**：通过美观的网页展示签到信息
4. **自动部署更新**：数据更新后自动部署到 GitHub Pages

## 项目结构

```
jetour_login/
├── .github/
│   └── workflows/
│       └── login.yml          # GitHub Actions 工作流配置
├── .nojekyll                  # GitHub Pages 配置文件
├── extract_jetour_sign_info.py # 签到信息提取脚本
├── index.html                 # 签到信息展示页面
├── jetour_configuration.yaml  # API 配置文件
├── requirements.txt           # Python 依赖文件
└── sign-data.json             # 签到数据文件
```

## 技术栈

- **前端**：HTML + Tailwind CSS + JavaScript
- **后端**：Python 3.12 + Requests
- **自动化**：GitHub Actions
- **部署**：GitHub Pages

## 配置说明

### 1. GitHub Secrets 配置

在 GitHub 仓库的 Settings > Secrets and variables > Actions 中添加以下 Secrets：

- `JETOUR_ACCESS_TOKEN`：捷途 API 访问令牌
- `JETOUR_TASK_ID`：捷途签到任务 ID

### 2. API 配置

API 配置文件为 `jetour_configuration.yaml`，包含以下 REST 命令配置：

- `jetour_sign_record`：获取签到记录
- `jetour_sign_page`：获取签到页面信息
- `jetour_task_load`：获取任务信息

## 工作流程

1. **定时触发**：每天 UTC 时间 0 点（北京时间 8 点）自动执行
2. **提取数据**：运行 Python 脚本从捷途 API 获取签到数据
3. **更新数据**：将提取的数据保存到 `sign-data.json` 文件
4. **部署更新**：将更新后的数据部署到 GitHub Pages
5. **访问展示**：通过 GitHub Pages 访问签到信息展示页面

## 手动触发

除了定时执行外，还可以通过以下方式手动触发工作流：

1. 进入 GitHub 仓库的 Actions 页面
2. 选择 "Jetour Sign Info Extraction" 工作流
3. 点击 "Run workflow" 按钮
4. 在弹出的对话框中点击 "Run workflow" 确认

## 页面访问

部署成功后，可以通过以下地址访问签到信息展示页面：

```
https://<username>.github.io/<repository-name>/
```

## 开发与测试

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行脚本

```bash
# 设置环境变量
export ACCESS_TOKEN="your-access-token"
export TASK_ID="your-task-id"

# 运行脚本
python extract_jetour_sign_info.py
```

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。
