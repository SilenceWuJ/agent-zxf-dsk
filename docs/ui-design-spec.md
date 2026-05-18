# UI 设计规范

## 设计系统

### 色彩系统

#### 主色板 (Primary Colors)

| 用途 | 色值 | 使用场景 |
|------|------|----------|
| 背景渐变起始 | `#0c1445` | 主页背景起点 |
| 背景渐变中间 | `#1a1f5c` | 主页背景过渡 |
| 背景渐变过渡 | `#2d1b4e` | 主页背景过渡 |
| 背景渐变终点 | `#1d3a5c` | 主页背景终点 |

#### 强调色 (Accent Colors)

| 名称 | 色值 | 渐变组合 | 用途 |
|------|------|----------|------|
| 青绿 | `#00f5d4` → `#00d4ff` | linear-gradient(135deg, #00f5d4 0%, #00d4ff 100%) | AI 智能体、科技感组件 |
| 绿色 | `#34d399` → `#10b981` | linear-gradient(135deg, #34d399 0%, #10b981 100%) | 工具、稳定功能 |
| 橙色 | `#fb923c` → `#f97316` | linear-gradient(135deg, #fb923c 0%, #f97316 100%) | 警告、QA 平台 |
| 紫色 | `#7b68ee` | 单色 | 知识、教育相关 |
| 粉色 | `#f472b6` | 单色 | 创意、艺术元素 |

#### 文字颜色

| 用途 | 色值 | 透明度 |
|------|------|--------|
| 主标题 | `white` | 100% |
| 副标题 | `white` | 80% |
| 正文 | `white` | 100% |
| 辅助文字 | `white` | 55% |
| 标签文字 | `white` | 60-65% |

#### 玻璃态效果

```css
background: rgba(255, 255, 255, 0.06);
backdrop-filter: blur(16px);
-webkit-backdrop-filter: blur(16px);
border: 1px solid rgba(255, 255, 255, 0.10);
```

### 间距系统

| 用途 | 桌面 (>640px) | 平板 (480-640px) | 移动 (<480px) |
|------|---------------|------------------|---------------|
| 容器 padding | 40px | 20px | 14px |
| 卡片 gap | 16px | 14px | 12px |
| 标题-卡片间距 | 36px | 28px | 20px |
| 卡片内部 padding | 28px 20px 22px | 22px 18px 18px | 16px 14px 14px |
| 标题-内容间距 | 8px | 6px | 5px |
| 按钮 padding | 9px 20px | 8px 16px | 7px 14px |

### 字体系统

#### 字体族
```css
font-family: 'Noto Sans SC', sans-serif;
```

#### 字号与字重

| 元素 | 桌面 | 平板 | 移动 | 字重 |
|------|------|------|------|------|
| 主标题 (h1) | 2.6rem | 1.8rem | 1.4rem | 700 |
| 卡片标题 (h3) | 1.1rem | 1rem | 0.9rem | 600 |
| 副标题 | 1.1rem | 0.95rem | 0.9rem | 300 |
| 正文 | 0.82rem | 0.8rem | 0.75rem | 400 |
| 辅助文字 | 0.7rem | 0.65rem | 0.6rem | 400 |
| 按钮 | 0.85rem | 0.8rem | 0.75rem | 600 |

## 组件规范

### 卡片组件 (Card)

#### 基础结构
```html
<div class="card card-[variant]">
    <div class="card-icon"><i class="fas fa-[icon]"></i></div>
    <div class="card-body">
        <h3>标题</h3>
        <p>描述内容</p>
    </div>
    <div class="card-right">
        <!-- 额外内容/按钮 -->
    </div>
</div>
```

#### 样式规格
- 圆角：18px (桌面) / 16px (平板) / 12px (移动)
- 顶边渐变条：4px 高度
- hover 位移：translateY(-6px)
- 过渡时间：0.35s cubic-bezier(0.4, 0, 0.2, 1)

#### 变体 (Variants)
- `card-cyborg` - 青绿渐变
- `card-tool` - 绿色渐变
- `card-qa` - 橙色渐变
- `card-resume` - 紫色渐变
- `card-portfolio` - 粉色渐变

### 按钮组件 (Button)

#### 基础样式
```css
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 9px 20px;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    color: white;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
}
```

#### 变体
- `btn-cyborg` - 青绿渐变
- `btn-tool` - 绿色渐变
- `btn-qa` - 橙色渐变
- `btn-resume` - 紫色渐变

### 标签组件 (Tag)

#### 技能标签
```css
.skill-tag {
    background: rgba(255, 255, 255, 0.07);
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.6);
}
```

#### 业绩标签
```css
.achievement-tag {
    background: linear-gradient(135deg, rgba(0, 245, 212, 0.2), rgba(0, 212, 255, 0.2));
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    color: rgba(0, 245, 212, 0.9);
    border: 1px solid rgba(0, 245, 212, 0.3);
}
```

### 图标组件 (Icon)

#### 卡片图标
```css
.card-icon {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    color: white;
    margin-bottom: 14px;
}
```

#### 尺寸变体
- 大 (large): 56px × 56px, 1.5rem icon
- 中 (medium): 48px × 48px, 1.3rem icon
- 小 (small): 40px × 40px, 1.1rem icon

## 布局规范

### 网格布局

#### 主页卡片网格
- 桌面 (>820px): 3 列
- 平板 (640-820px): 2 列
- 移动 (<640px): 1 列

```css
.category-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}

@media (max-width: 820px) {
    .category-cards {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 640px) {
    .category-cards {
        grid-template-columns: 1fr;
    }
}
```

### 页面结构

```
┌─────────────────────────────────────┐
│           Header (顶部)             │
│     Logo/Title + Navigation         │
├─────────────────────────────────────┤
│                                     │
│          Hero Section               │
│        个人信息 + 简介               │
│                                     │
├─────────────────────────────────────┤
│                                     │
│         Category Cards              │
│        快捷入口卡片网格              │
│                                     │
├─────────────────────────────────────┤
│                                     │
│         Recent Works                │
│         近期作品展示                 │
│                                     │
├─────────────────────────────────────┤
│           Footer (底部)             │
│         Copyright 信息               │
└─────────────────────────────────────┘
```

## 动画规范

### 过渡动画
- 卡片 hover: `0.35s cubic-bezier(0.4, 0, 0.2, 1)`
- 按钮 hover: `0.3s ease`
- 页面加载: `0.5s ease`

### 渐入动画
```css
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

### 渐变文字动画
```css
@keyframes gradientMove {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
```

## 响应式断点

| 断点名称 | 宽度范围 | 设备类型 |
|----------|----------|----------|
| mobile-xs | < 360px | 超小手机 |
| mobile-sm | 360px - 480px | 小屏手机 |
| mobile-md | 480px - 640px | 大屏手机 |
| tablet | 640px - 1024px | 平板 |
| desktop | > 1024px | 桌面 |

## Figma 设计参考

### 需要创建的设计资产

1. **色彩变量** - 创建 Styles:
   - `primary-gradient`: #0c1445 → #1d3a5c
   - `accent-cyan`: #00f5d4 → #00d4ff
   - `accent-green`: #34d399 → #10b981
   - `accent-orange`: #fb923c → #f97316
   - `accent-purple`: #7b68ee
   - `accent-pink`: #f472b6

2. **组件库**:
   - Card Base (基础卡片)
   - Card with Icon (带图标卡片)
   - Button Primary/Secondary
   - Tag (标签)
   - Hero Section (个人信息区)
   - Timeline Item (时间轴项)

3. **页面布局**:
   - Home - Desktop (1920×1080)
   - Home - Mobile (375×812)
   - Resume Page
   - Portfolio Page
   - Projects Page

### 命名规范
- 组件: `Component/Name`
- 页面: `Page/Name`
- 颜色: `Color/Usage/Variant`
- 文字: `Text/Usage/Size/Weight`