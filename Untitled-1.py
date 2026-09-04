import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import importlib
import json
import matplotlib.pyplot as plt
import numpy as np

# ==================== 中文字体配置 ====================
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
FONT_FAMILY = 'Microsoft YaHei'  # Windows 通用，macOS 可改为 'PingFang SC'

def load_players(file_path):
    """读取 CSV、JSON 或 Excel，并统一为程序内部使用的字段名。"""
    required = {'name', 'team', 'k', 'd', 'a', 'first', 'dmg', 'acs'}
    aliases = {
        '选手': 'name', '选手名': 'name', '玩家': 'name', 'name': 'name',
        '队伍': 'team', '阵营': 'team', 'team': 'team',
        '击杀': 'k', 'k': 'k', '死亡': 'd', 'd': 'd', '助攻': 'a', 'a': 'a',
        '首杀': 'first', 'first': 'first', '伤害': 'dmg', '回合均伤': 'dmg', 'dmg': 'dmg',
        'acs': 'acs', '战斗评分': 'acs', '回合均分': 'acs',
    }
    suffix = file_path.lower().rsplit('.', 1)[-1]
    if suffix == 'csv':
        with open(file_path, 'r', encoding='utf-8-sig', newline='') as file:
            rows = list(csv.DictReader(file))
    elif suffix == 'json':
        with open(file_path, 'r', encoding='utf-8') as file:
            rows = json.load(file)
    elif suffix in {'xlsx', 'xls'}:
        try:
            pd = importlib.import_module('pandas')
            rows = pd.read_excel(file_path).to_dict('records')
        except ImportError as error:
            raise ValueError('读取 Excel 需要安装 pandas 和 openpyxl') from error
    else:
        raise ValueError('仅支持 CSV、JSON 或 Excel 文件')

    if not isinstance(rows, list) or not rows:
        raise ValueError('文件中没有选手数据')
    normalized = []
    for row in rows:
        converted = {aliases.get(str(key).strip(), str(key).strip()): value for key, value in row.items()}
        missing = required - converted.keys()
        if missing:
            raise ValueError(f'缺少字段：{", ".join(sorted(missing))}')
        try:
            player = {key: converted[key] for key in required}
            team_aliases = {'红方': '我方', '蓝方': '敌方', '红队': '我方', '蓝队': '敌方'}
            player['team'] = team_aliases.get(str(player['team']).strip(), str(player['team']).strip())
            for key in required - {'name', 'team'}:
                player[key] = float(player[key])
                if player[key].is_integer():
                    player[key] = int(player[key])
        except (TypeError, ValueError) as error:
            raise ValueError(f'选手数据包含无法识别的数字：{row}') from error
        normalized.append(player)
    return normalized


# ==================== 1. 启动时选择并提取数据 ====================
total_rounds = 18
startup_root = tk.Tk()
startup_root.withdraw()
data_file = filedialog.askopenfilename(
    title='选择选手原始数据文件',
    filetypes=[('数据文件', '*.csv *.json *.xlsx *.xls'), ('所有文件', '*.*')],
)
if not data_file:
    startup_root.destroy()
    raise SystemExit
try:
    players_raw = load_players(data_file)
except (OSError, ValueError) as error:
    messagebox.showerror('数据读取失败', str(error), parent=startup_root)
    startup_root.destroy()
    raise SystemExit
if len(players_raw) != 10:
    messagebox.showwarning(
        '数据数量提示',
        f'已读取 {len(players_raw)} 名选手，建议文件包含我方和敌方各 5 名。',
        parent=startup_root,
    )
startup_root.destroy()

labels = ['回合均伤', '回合均分', '存活率', '首杀率', '回合均助', '回合均杀']

# 计算原始六维值
for p in players_raw:
    p['回合均伤'] = p['dmg']
    p['回合均分'] = p['acs']
    p['存活率'] = max(0, (total_rounds - p['d']) / total_rounds)
    p['首杀率'] = p['first'] / total_rounds
    p['回合均助'] = p['a'] / total_rounds
    p['回合均杀'] = p['k'] / total_rounds

red_team = [p for p in players_raw if p['team'] == '我方']
blue_team = [p for p in players_raw if p['team'] == '敌方']
all_players = red_team + blue_team

# 全局最值
min_vals = {label: min(p[label] for p in all_players) for label in labels}
max_vals = {label: max(p[label] for p in all_players) for label in labels}

# 归一化：将 [min, max] 映射到 [5, 100]，避免图形坍缩
def normalize(value, label):
    mn, mx = min_vals[label], max_vals[label]
    if mx == mn:
        return 50
    # 线性映射到 5 ~ 100
    return 5 + (value - mn) / (mx - mn) * 95

for p in all_players:
    p['norm'] = {label: normalize(p[label], label) for label in labels}

# 辅助函数：提取纯名字（去掉 # 及后面数字）
def get_plain_name(full_name):
    return full_name.split('#')[0]

# ==================== 2. 绘图函数 ====================
def plot_all_comparisons(pairings):
    """
    pairings: 列表，每个元素为 (red_dict, blue_dict)
    其中 dict 中已包含 'display_name' 字段
    """
    valid_pairs = [p for p in pairings if p is not None]
    if not valid_pairs:
        print("没有有效的配对")
        return

    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles_closed = angles + angles[:1]

    fig, axes = plt.subplots(2, 3, figsize=(18, 12), subplot_kw={'polar': True})
    axes_flat = axes.flatten()

    for idx, (red, blue) in enumerate(valid_pairs):
        if idx >= 5:
            break
        ax = axes_flat[idx]

        ax.set_theta_offset(np.pi / 2 - np.pi / 6)  # 旋转30°
        ax.set_theta_direction(-1)

        vals_red = [red['norm'][lbl] for lbl in labels] + [red['norm'][labels[0]]]
        vals_blue = [blue['norm'][lbl] for lbl in labels] + [blue['norm'][labels[0]]]

        # 使用 display_name
        ax.plot(angles_closed, vals_red, 'o-', linewidth=2.5, color='red', label=red['display_name'])
        ax.fill(angles_closed, vals_red, alpha=0.2, color='red')
        ax.plot(angles_closed, vals_blue, 'o-', linewidth=2.5, color='blue', label=blue['display_name'])
        ax.fill(angles_closed, vals_blue, alpha=0.2, color='blue')

        ax.set_xticks(angles)
        label_texts = [f'{lbl}\n({min_vals[lbl]:.2f}~{max_vals[lbl]:.2f})' for lbl in labels]
        ax.set_xticklabels(label_texts, fontsize=9, fontweight='bold')

        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8)
        ax.grid(True, linestyle='--', alpha=0.6)

        ax.set_title(f'组{idx+1}: {red["display_name"]} vs {blue["display_name"]}', size=12, pad=15)
        ax.legend(loc='upper right', bbox_to_anchor=(1.1, 1.0), fontsize=10)

    if len(valid_pairs) < 6:
        axes_flat[5].axis('off')

    plt.suptitle('无畏契约对局选手自定义配对对比雷达图（动态归一化 5~100，旋转30°）',
                 size=20, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.show()

# ==================== 3. GUI界面 ====================
def on_generate():
    # 读取组号和英雄名
    red_groups = []
    red_display = []
    for spin, entry in zip(red_spins, red_hero_entries):
        try:
            g = int(spin.get())
            if g < 1 or g > 5:
                raise ValueError
            red_groups.append(g)
        except:
            messagebox.showerror("错误", "组号必须为1-5的整数")
            return
        hero = entry.get().strip()
        red_display.append(hero)

    blue_groups = []
    blue_display = []
    for spin, entry in zip(blue_spins, blue_hero_entries):
        try:
            g = int(spin.get())
            if g < 1 or g > 5:
                raise ValueError
            blue_groups.append(g)
        except:
            messagebox.showerror("错误", "组号必须为1-5的整数")
            return
        hero = entry.get().strip()
        blue_display.append(hero)

    # 构建配对
    pairings = [None] * 5
    # 先处理红方
    for i, g in enumerate(red_groups):
        idx = g - 1
        player = red_team[i].copy()  # 避免修改原始数据
        # 决定显示名称
        if red_display[i]:
            player['display_name'] = red_display[i]
        else:
            player['display_name'] = get_plain_name(player['name'])
        if pairings[idx] is None:
            pairings[idx] = (player, None)
        else:
            pairings[idx] = (player, pairings[idx][1])

    # 再处理蓝方
    for i, g in enumerate(blue_groups):
        idx = g - 1
        player = blue_team[i].copy()
        if blue_display[i]:
            player['display_name'] = blue_display[i]
        else:
            player['display_name'] = get_plain_name(player['name'])
        if pairings[idx] is None:
            pairings[idx] = (None, player)
        else:
            pairings[idx] = (pairings[idx][0], player)

    # 检查完整性
    valid_pairs = []
    for idx, pair in enumerate(pairings):
        if pair is None:
            messagebox.showwarning("警告", f"组{idx+1}没有分配任何选手")
            continue
        red, blue = pair
        if red is None or blue is None:
            messagebox.showwarning("警告", f"组{idx+1}缺少红方或蓝方选手")
            continue
        valid_pairs.append(pair)

    if not valid_pairs:
        messagebox.showerror("错误", "没有完整的配对，无法生成")
        return

    plot_all_comparisons(valid_pairs)

# 创建主窗口
root = tk.Tk()
root.title("无畏契约对位配对工具")
root.geometry("850x550")

default_font = (FONT_FAMILY, 10)
root.option_add("*Font", default_font)

main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

# 左侧红方
red_frame = tk.Frame(main_frame)
red_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

tk.Label(red_frame, text="我方（红色）", fg="red", font=(FONT_FAMILY, 14, "bold")).pack(pady=5)

red_spins = []
red_hero_entries = []
for p in red_team:
    sub = tk.Frame(red_frame)
    sub.pack(pady=2, anchor='w')
    # 选手名
    tk.Label(sub, text=p['name'], width=20, anchor='w', font=(FONT_FAMILY, 10)).pack(side=tk.LEFT)
    # 组号 Spinbox
    spin = tk.Spinbox(sub, from_=1, to=5, width=4, state='readonly', font=(FONT_FAMILY, 10))
    spin.delete(0, tk.END)
    spin.insert(0, "1")
    spin.pack(side=tk.LEFT, padx=(5, 10))
    red_spins.append(spin)
    # 英雄名称 Entry
    entry = tk.Entry(sub, width=12, font=(FONT_FAMILY, 10))
    entry.pack(side=tk.LEFT)
    red_hero_entries.append(entry)

# 右侧蓝方
blue_frame = tk.Frame(main_frame)
blue_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

tk.Label(blue_frame, text="敌方（蓝色）", fg="blue", font=(FONT_FAMILY, 14, "bold")).pack(pady=5)

blue_spins = []
blue_hero_entries = []
for p in blue_team:
    sub = tk.Frame(blue_frame)
    sub.pack(pady=2, anchor='w')
    tk.Label(sub, text=p['name'], width=20, anchor='w', font=(FONT_FAMILY, 10)).pack(side=tk.LEFT)
    spin = tk.Spinbox(sub, from_=1, to=5, width=4, state='readonly', font=(FONT_FAMILY, 10))
    spin.delete(0, tk.END)
    spin.insert(0, "1")
    spin.pack(side=tk.LEFT, padx=(5, 10))
    blue_spins.append(spin)
    entry = tk.Entry(sub, width=12, font=(FONT_FAMILY, 10))
    entry.pack(side=tk.LEFT)
    blue_hero_entries.append(entry)

# 生成按钮
btn = tk.Button(root, text="生成五组对比图", command=on_generate,
                font=(FONT_FAMILY, 14), bg="#FF4655", fg="white")
btn.pack(pady=15)

root.mainloop()