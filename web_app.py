import csv
import io
import json

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st


TOTAL_ROUNDS = 18
LABELS = ['回合均伤', '回合均分', '存活率', '首杀率', '回合均助', '回合均杀']
REQUIRED = {'name', 'team', 'k', 'd', 'a', 'first', 'dmg', 'acs'}
ALIASES = {
    '选手': 'name', '选手名': 'name', '玩家': 'name', 'name': 'name',
    '队伍': 'team', '阵营': 'team', 'team': 'team',
    '击杀': 'k', 'k': 'k', '死亡': 'd', 'd': 'd', '助攻': 'a', 'a': 'a',
    '首杀': 'first', '首杀数': 'first', 'first': 'first',
    '伤害': 'dmg', '回合均伤': 'dmg', 'dmg': 'dmg',
    'acs': 'acs', '战斗评分': 'acs', '回合均分': 'acs',
}
TEAM_ALIASES = {'红方': '我方', '蓝方': '敌方', '红队': '我方', '蓝队': '敌方'}


@st.cache_data(show_spinner=False)
def load_players(file_name, file_bytes):
    suffix = file_name.lower().rsplit('.', 1)[-1]
    if suffix == 'csv':
        rows = list(csv.DictReader(io.StringIO(file_bytes.decode('utf-8-sig'))))
    elif suffix == 'json':
        rows = json.loads(file_bytes.decode('utf-8'))
    elif suffix in {'xlsx', 'xls'}:
        import pandas as pd
        rows = pd.read_excel(io.BytesIO(file_bytes)).to_dict('records')
    else:
        raise ValueError('仅支持 CSV、JSON 或 Excel 文件')

    if not isinstance(rows, list) or not rows:
        raise ValueError('文件中没有选手数据')
    players = []
    for row in rows:
        converted = {ALIASES.get(str(key).strip(), str(key).strip()): value for key, value in row.items()}
        missing = REQUIRED - converted.keys()
        if missing:
            raise ValueError(f'缺少字段：{", ".join(sorted(missing))}')
        try:
            player = {key: converted[key] for key in REQUIRED}
            player['name'] = str(player['name']).strip()
            player['team'] = TEAM_ALIASES.get(str(player['team']).strip(), str(player['team']).strip())
            for key in REQUIRED - {'name', 'team'}:
                player[key] = float(player[key])
        except (TypeError, ValueError) as error:
            raise ValueError(f'选手数据包含无法识别的数字：{row}') from error
        players.append(player)
    return players


def prepare_players(players):
    for player in players:
        player['回合均伤'] = player['dmg']
        player['回合均分'] = player['acs']
        player['存活率'] = max(0, (TOTAL_ROUNDS - player['d']) / TOTAL_ROUNDS)
        player['首杀率'] = player['first'] / TOTAL_ROUNDS
        player['回合均助'] = player['a'] / TOTAL_ROUNDS
        player['回合均杀'] = player['k'] / TOTAL_ROUNDS
    min_vals = {label: min(player[label] for player in players) for label in LABELS}
    max_vals = {label: max(player[label] for player in players) for label in LABELS}
    for player in players:
        player['norm'] = {
            label: 50 if min_vals[label] == max_vals[label] else
            5 + (player[label] - min_vals[label]) / (max_vals[label] - min_vals[label]) * 95
            for label in LABELS
        }
    return min_vals, max_vals


def make_chart(pairings, min_vals, max_vals):
    angles = np.linspace(0, 2 * np.pi, len(LABELS), endpoint=False).tolist()
    closed_angles = angles + angles[:1]
    figure, axes = plt.subplots(2, 3, figsize=(16, 10), subplot_kw={'polar': True})
    axes_flat = axes.flatten()
    for index, (red, blue) in enumerate(pairings):
        axis = axes_flat[index]
        axis.set_theta_offset(np.pi / 2 - np.pi / 6)
        axis.set_theta_direction(-1)
        red_values = [red['norm'][label] for label in LABELS] + [red['norm'][LABELS[0]]]
        blue_values = [blue['norm'][label] for label in LABELS] + [blue['norm'][LABELS[0]]]
        axis.plot(closed_angles, red_values, 'o-', linewidth=2.5, color='#e5484d', label=red['display_name'])
        axis.fill(closed_angles, red_values, alpha=0.2, color='#e5484d')
        axis.plot(closed_angles, blue_values, 'o-', linewidth=2.5, color='#2878d0', label=blue['display_name'])
        axis.fill(closed_angles, blue_values, alpha=0.2, color='#2878d0')
        axis.set_xticks(angles)
        axis.set_xticklabels([f'{label}\n({min_vals[label]:.2f}~{max_vals[label]:.2f})' for label in LABELS], fontsize=8)
        axis.set_ylim(0, 100)
        axis.set_yticks([20, 40, 60, 80, 100])
        axis.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=7)
        axis.grid(True, linestyle='--', alpha=0.6)
        axis.set_title(f'组{index + 1}: {red["display_name"]} vs {blue["display_name"]}', fontsize=11, pad=14)
        axis.legend(loc='upper right', bbox_to_anchor=(1.12, 1.0), fontsize=8)
    for axis in axes_flat[len(pairings):]:
        axis.axis('off')
    figure.suptitle('无畏契约对位雷达图', fontsize=19, fontweight='bold')
    figure.tight_layout()
    return figure


st.set_page_config(page_title='无畏契约对位工具', page_icon='⚔️', layout='wide')
st.markdown('''
<style>
    .block-container { max-width: 1280px; padding-top: 2.5rem; }
    h1 { letter-spacing: 0; color: #182230; }
    [data-testid="stFileUploader"] { border: 1px solid #d8dee8; padding: 1rem; border-radius: 8px; background: #f7f9fc; }
    div[data-testid="stButton"] > button { background: #e5484d; color: white; border: 0; border-radius: 6px; font-weight: 700; }
</style>
''', unsafe_allow_html=True)
st.title('无畏契约对位工具')
st.caption('上传选手原始数据，设置对位组和英雄名称，然后生成对比雷达图。')

uploaded_file = st.file_uploader('选择选手原始数据文件', type=['csv', 'json', 'xlsx', 'xls'])
if uploaded_file is None:
    st.info('请先上传 CSV、JSON 或 Excel 文件。')
    st.stop()

try:
    players = load_players(uploaded_file.name, uploaded_file.getvalue())
    min_vals, max_vals = prepare_players(players)
except Exception as error:
    st.error(f'数据读取失败：{error}')
    st.stop()

red_team = [player for player in players if player['team'] == '我方']
blue_team = [player for player in players if player['team'] == '敌方']
if not red_team or not blue_team:
    st.error('没有识别到完整的我方和敌方数据，请检查 team/队伍 字段。')
    st.stop()
if len(red_team) != 5 or len(blue_team) != 5:
    st.warning(f'当前读取我方 {len(red_team)} 人、敌方 {len(blue_team)} 人，建议双方各 5 人。')

st.subheader('设置对位')
left, right = st.columns(2)
red_groups = []
blue_groups = []
red_names = []
blue_names = []
with left:
    st.markdown('#### 我方（红色）')
    for index, player in enumerate(red_team):
        group_col, hero_col = st.columns([1, 2])
        with group_col:
            red_groups.append(st.selectbox(f'{player["name"]} 组', range(1, 6), key=f'red_group_{index}'))
        with hero_col:
            red_names.append(st.text_input('英雄名称', key=f'red_hero_{index}', placeholder='可选'))
with right:
    st.markdown('#### 敌方（蓝色）')
    for index, player in enumerate(blue_team):
        group_col, hero_col = st.columns([1, 2])
        with group_col:
            blue_groups.append(st.selectbox(f'{player["name"]} 组', range(1, 6), key=f'blue_group_{index}'))
        with hero_col:
            blue_names.append(st.text_input('英雄名称', key=f'blue_hero_{index}', placeholder='可选'))

if st.button('生成五组对比图', type='primary', use_container_width=True):
    pairings = [None] * 5
    for team, groups, display_names in ((red_team, red_groups, red_names), (blue_team, blue_groups, blue_names)):
        for index, group in enumerate(groups):
            player = team[index].copy()
            player['display_name'] = display_names[index].strip() or player['name'].split('#')[0]
            pair_index = group - 1
            existing = pairings[pair_index]
            pairings[pair_index] = (player, existing[1]) if team is red_team and existing else (existing[0], player) if existing else (player, None) if team is red_team else (None, player)
    valid_pairings = [pair for pair in pairings if pair and pair[0] and pair[1]]
    if not valid_pairings:
        st.error('没有完整的配对，无法生成图表。')
    else:
        st.pyplot(make_chart(valid_pairings, min_vals, max_vals), clear_figure=True)
        missing_count = 5 - len(valid_pairings)
        if missing_count:
            st.warning(f'已生成 {len(valid_pairings)} 组完整对位，另有 {missing_count} 组不完整。')
