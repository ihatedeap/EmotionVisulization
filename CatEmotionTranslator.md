# Cat Emotion Translator - Development Documentation

> 📅 **Last Updated**: 2026-03-12

## 项目目标

1. **数据收集**：通过放置在猫尾巴根部的传感器（加速度计+陀螺仪）收集数据
2. **情绪识别**：使用决策树算法识别猫咪的各种情绪状态
3. **表情输出**：通过第二块ESP32接收传感器数据，输入决策树模型，输出对应表情到屏幕显示

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           阶段1：数据收集与标注                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐      I2C       ┌─────────┐      WiFi      ┌─────────────┐     │
│  │  MPU6050    │◄──────────────►│ ESP32-1 │◄──────────────►│  Supabase   │     │
│  │   Sensor    │                │(数据采集)│                │   Cloud DB  │     │
│  └─────────────┘                └─────────┘                └──────┬──────┘     │
│                                                                    │            │
│                                                                    │ Realtime   │
│                                                                    ▼            │
│                                                             ┌─────────────┐     │
│                                                             │ label.html  │     │
│                                                             │  情绪标注页面 │     │
│                                                             └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ 标注数据用于训练
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           阶段2：决策树模型训练（PC端）                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         PC 训练流程                                       │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │   │
│  │  │ 从Supabase │───►│ 数据预处理 │───►│ 决策树训练 │───►│ 导出模型(.json)  │  │   │
│  │  │ 下载数据  │    │ 特征提取  │    │ 模型优化  │    │ 用于ESP32推理    │  │   │
│  │  └──────────┘    └──────────┘    └──────────┘    └──────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ 导出训练好的模型
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           阶段3：实时情绪识别与表情显示                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐      I2C       ┌─────────┐                              │
│  │  MPU6050    │◄──────────────►│ ESP32-2 │                              │
│  │   Sensor    │                │(推理显示)│      ┌─────────────┐        │
│  └─────────────┘                └────┬────┘─────►│ OLED/LCD    │        │
│                                      │            │  表情屏幕    │        │
│                                      │            │  😺 😸 😾    │        │
│                                      │            └─────────────┘        │
│                                      │                                     │
│                        ┌─────────────┴─────────────┐                     │
│                        │     内置决策树模型推理      │                     │
│                        │  (输入: pitch/roll/gyro)   │                     │
│                        │  (输出: 情绪类别)          │                     │
│                        └───────────────────────────┘                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
├── CatEmotionTranslator.md
├── web/
│   ├── label.html              # 情绪标注页面
│   ├── supabase_config.js      # Supabase配置
│   ├── style.css
│   ├── app.js
├── ESP32/
│   ├── ESP32.code-workspace
│   ├── supabase_data_collection.py  # ESP32-1: 数据采集上传
│   ├── emotion_display.py           # ESP32-2: 实时推理+表情显示
│   ├── decision_tree_model.json     # 训练好的决策树模型
│   ├── secrets.py
├── pc_training/
│   ├── train_decision_tree.py       # 决策树训练脚本
│   ├── data_preprocessing.py        # 数据预处理
│   ├── model_export.py              # 模型导出为ESP32可用格式
│   └── requirements.txt
```

## 阶段1：数据收集

### 硬件配置

**ESP32-1 (数据采集端)**

| ESP32 引脚 | MPU6050 引脚 | 说明 |
|-----------|-------------|------|
| GPIO 4 | SCL | I2C 时钟线 |
| GPIO 5 | SDA | I2C 数据线 |
| 3.3V | VCC | 电源正极 |
| GND | GND | 电源负极 |

### 传感器配置

- **I2C 地址**: `0x68`
- **采样频率**: 400kHz
- **加速度量程**: ±4g（适合姿态检测）
- **陀螺仪量程**: ±500°/s

### 数据上传格式

- **上传间隔**: 200ms (5Hz)
- **数据字段**: `ax`, `ay`, `az`, `pitch`, `roll`, `gyro_x`, `gyro_y`, `gyro_z`
- **Device ID**: `esp32_01`

### 情绪标签

| 情绪 | 说明 |
|------|------|
| 撒娇 | 尾巴轻柔摇摆，姿态放松 |
| 放松 | 尾巴自然下垂或平放 |
| 有兴趣 | 尾巴竖起，可能有轻微摆动 |
| 攻击 | 尾巴僵硬，快速甩动 |
| 焦躁 | 尾巴快速拍打 |
| 恐惧 | 尾巴夹紧，身体蜷缩 |

## 阶段2：决策树模型训练（PC端）

### 训练流程

```
原始传感器数据
    ↓
[数据预处理]
    - 数据清洗（去除异常值）
    - 滑动窗口特征提取（窗口大小: 50帧, 步长: 25帧）
    - 计算统计特征: 均值、方差、最大值、最小值、过零率
    ↓
[特征工程]
    - pitch_mean, pitch_std, pitch_max, pitch_min
    - roll_mean, roll_std, roll_max, roll_min
    - gyro_magnitude_mean, gyro_magnitude_std
    - tail_movement_frequency (尾巴摆动频率)
    ↓
[决策树训练]
    - 算法: CART (Classification and Regression Tree)
    - 最大深度: 8
    - 最小分裂样本: 5
    - 交叉验证: 5折
    ↓
[模型优化]
    - 剪枝优化
    - 超参数调优
    ↓
[模型导出]
    - 导出为 JSON 格式
    - 适配 ESP32 MicroPython 解析
```

### 训练代码示例

```python
# pc_training/train_decision_tree.py
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split, cross_val_score
import json

# 1. 加载数据
# data = load_from_supabase(...)

# 2. 特征提取
# X = extract_features(data)  # 形状: (n_samples, n_features)
# y = data['emotion_label']    # 情绪标签

# 3. 训练决策树
clf = DecisionTreeClassifier(
    max_depth=8,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42
)
clf.fit(X_train, y_train)

# 4. 评估
scores = cross_val_score(clf, X, y, cv=5)
print(f"交叉验证准确率: {scores.mean():.3f} ± {scores.std():.3f}")

# 5. 导出为ESP32可用格式
def export_tree_to_json(tree, feature_names, class_names, filepath):
    """将决策树导出为ESP32可解析的JSON格式"""
    tree_structure = {
        'feature_names': feature_names,
        'class_names': class_names,
        'tree': serialize_tree(tree.tree_)
    }
    with open(filepath, 'w') as f:
        json.dump(tree_structure, f)

export_tree_to_json(clf, feature_names, class_names, 'decision_tree_model.json')
```

### 决策树模型JSON格式

```json
{
  "feature_names": ["pitch_mean", "pitch_std", "roll_mean", "roll_std", "gyro_mag_mean"],
  "class_names": ["撒娇", "放松", "有兴趣", "攻击", "焦躁", "恐惧"],
  "tree": {
    "feature": 1,
    "threshold": 15.0,
    "left": {
      "feature": 3,
      "threshold": 10.0,
      "left": { "class": "放松" },
      "right": { "class": "有兴趣" }
    },
    "right": {
      "feature": 4,
      "threshold": 50.0,
      "left": { "class": "撒娇" },
      "right": { "class": "攻击" }
    }
  }
}
```

## 阶段3：实时情绪识别与表情显示

### 硬件配置

**ESP32-2 (推理+显示端)**

| ESP32-2 引脚 | 设备 | 说明 |
|-------------|------|------|
| GPIO 4 | MPU6050 SCL | I2C 时钟线 |
| GPIO 5 | MPU6050 SDA | I2C 数据线 |
| GPIO 18 | OLED SCL | 屏幕时钟线 (SPI/I2C) |
| GPIO 19 | OLED SDA | 屏幕数据线 |
| GPIO 21 | OLED DC | 数据/命令选择 |
| GPIO 22 | OLED CS | 片选 |
| GPIO 23 | OLED RST | 复位 |

### 情绪-表情映射表

| 情绪 | 表情符号 | 屏幕显示 | 颜色 |
|------|---------|---------|------|
| 撒娇 | 🥺 | 卖萌脸 | 粉色 |
| 放松 | 😌 | 舒适脸 | 绿色 |
| 有兴趣 | 👀 | 好奇脸 | 蓝色 |
| 攻击 | 😾 | 愤怒脸 | 红色 |
| 焦躁 | 😤 | 烦躁脸 | 橙色 |
| 恐惧 | 😰 | 害怕脸 | 紫色 |

### ESP32-2 推理显示代码

```python
# ESP32/emotion_display.py
import json
from machine import Pin, SPI, I2C
import framebuf

# 加载决策树模型
with open('decision_tree_model.json', 'r') as f:
    model = json.load(f)

def predict_emotion(features):
    """使用决策树模型进行推理"""
    node = model['tree']
    while 'class' not in node:
        feature_idx = node['feature']
        threshold = node['threshold']
        if features[feature_idx] <= threshold:
            node = node['left']
        else:
            node = node['right']
    return node['class']

def extract_features(sensor_buffer):
    """从传感器缓冲区提取特征"""
    # 计算 pitch/roll/gyro 的统计特征
    # 返回特征向量
    pass

# 表情位图数据 (16x16 or 32x32)
emotion_bitmaps = {
    '撒娇': bytes([...]),  # 卖萌脸位图
    '放松': bytes([...]),  # 舒适脸位图
    '有兴趣': bytes([...]), # 好奇脸位图
    '攻击': bytes([...]),   # 愤怒脸位图
    '焦躁': bytes([...]),   # 烦躁脸位图
    '恐惧': bytes([...])    # 害怕脸位图
}

emotion_colors = {
    '撒娇': 0xF81F,  # 粉色
    '放松': 0x07E0,  # 绿色
    '有兴趣': 0x001F, # 蓝色
    '攻击': 0xF800,   # 红色
    '焦躁': 0xFD20,   # 橙色
    '恐惧': 0x801F    # 紫色
}

def display_emotion(emotion, oled):
    """在OLED屏幕上显示表情"""
    oled.fill(0)  # 清屏
    bitmap = emotion_bitmaps[emotion]
    color = emotion_colors[emotion]
    # 绘制位图
    oled.blit(framebuf.FrameBuffer(bitmap, 32, 32, framebuf.MONO_HLSB), 48, 8)
    oled.show()

# 主循环
sensor_buffer = []
while True:
    # 1. 读取传感器数据
    data = read_mpu6050()
    sensor_buffer.append(data)
    
    # 2. 缓冲区满时进行推理
    if len(sensor_buffer) >= 50:  # 50帧 = 10秒 (5Hz采样)
        # 3. 特征提取
        features = extract_features(sensor_buffer)
        
        # 4. 决策树推理
        emotion = predict_emotion(features)
        
        # 5. 显示表情
        display_emotion(emotion, oled)
        
        # 清空缓冲区，保留重叠部分
        sensor_buffer = sensor_buffer[25:]  # 50% 重叠
```

### 屏幕显示效果

```
┌────────────────────────────┐
│                            │
│       ┌──────────┐         │
│       │          │         │
│       │   😾     │         │  ← 表情图标 (32x32)
│       │          │         │
│       └──────────┘         │
│                            │
│      情绪: 攻击            │  ← 情绪文字
│      置信度: 87%           │  ← 置信度 (可选)
│                            │
└────────────────────────────┘
```

## Database Schema

### sensor_data Table

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| device_id | text | Device identifier |
| ax, ay, az | integer | Raw acceleration values |
| pitch, roll | float | Calculated angles |
| gyro_x, gyro_y, gyro_z | float | Angular velocity |
| created_at | timestamptz | Timestamp |

### labels Table

| Field | Type | Description |
|-------|------|-------------|
| id | uuid | Primary key |
| device_id | text | Device identifier |
| emotion | text | Emotion label |
| start_time | timestamptz | Label start time |
| end_time | timestamptz | Label end time |

## Development Environment

### Recommended Tools

- **IDE**: VS Code + MicroPico extension
- **Serial Monitor**: minicom / putty / VS Code serial monitor
- **Browser**: Chrome / Edge / Safari
- **Python环境**: Python 3.8+ (用于模型训练)

### Dependencies

**ESP32 (MicroPython)**
- `machine`, `network`, `urequests`, `ujson`, `framebuf`

**PC端训练**
- `scikit-learn`, `numpy`, `pandas`, `supabase-py`

**Web Frontend**
- `@supabase/supabase-js@2` (CDN)

## Notes

1. **Security**: `secrets.py` contains sensitive data, already in `.gitignore`
2. **数据收集**: 收集多种场景下的数据以提高模型泛化能力
3. **模型优化**: 决策树深度不宜过大，避免在ESP32上推理过慢
4. **实时性**: ESP32-2的推理窗口和显示刷新率需要平衡
5. **电池续航**: 考虑使用低功耗模式延长佩戴时间

## Future Plans

- [ ] 增加陀螺仪数据用于更精确的姿态判断
- [ ] 实现本地数据缓存（离线模式）
- [ ] 支持更多情绪类别
- [ ] 添加手机APP实时查看
- [ ] 优化决策树模型，尝试随机森林算法
- [ ] 增加声音传感器，结合声音判断情绪

---

*此文档为手动维护，修改时请同步更新。*
