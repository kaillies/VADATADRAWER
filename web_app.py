import csv
import io
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from streamlit_sortables import sort_items
except ImportError:
    sort_items = None


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


def _ocr_lines(image):
    if pytesseract is None:
        raise ValueError('截图识别依赖尚未安装，请重新部署应用后再试')
    text = pytesseract.image_to_string(image, lang='chi_sim+eng', config='--psm 11')
    return [line.strip() for line in text.splitlines() if line.strip()]


def _number(value):
    try:
        return float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        return 0.0


def extract_screenshot_candidates(uploaded_files):
    lines = []
    for uploaded_file in uploaded_files:
        image = Image.open(io.BytesIO(uploaded_file.getvalue())).convert('RGB')
        image.thumbnail((900, 6000), Image.Resampling.LANCZOS)
        lines.extend(_ocr_lines(image))

    candidates = []
    kda_pattern = re.compile(r'(\d{1,2})\s*[/:|丨]\s*(\d{1,2})\s*[/:|丨]\s*(\d{1,2})')
    for line in lines:
        match = kda_pattern.search(line)
        if not match:
            continue
        prefix = line[:match.start()].strip(' |-:：')
        name_match = re.search(r'[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9_#-]{1,24}', prefix)
        name = name_match.group(0) if name_match else f'待确认选手{len(candidates) + 1}'
        prefix_numbers = re.findall(r'(?<!/)(\d+(?:\.\d+)?)', prefix)
        trailing_numbers = re.findall(r'(?<!/)(\d+(?:\.\d+)?)', line[match.end():])
        acs = _number(prefix_numbers[-1]) if prefix_numbers else _number(trailing_numbers[0]) if trailing_numbers else 0
        candidates.append({
            'name': name,
            'team': '我方' if len(candidates) < 5 else '敌方',
            'k': _number(match.group(1)),
            'd': _number(match.group(2)),
            'a': _number(match.group(3)),
            'first': 0,
            'dmg': 0,
            'acs': acs,
        })

    unique_candidates = []
    seen_stats = set()
    for candidate in candidates:
        stat_key = (candidate['k'], candidate['d'], candidate['a'])
        if stat_key not in seen_stats:
            unique_candidates.append(candidate)
            seen_stats.add(stat_key)
    candidates = unique_candidates
    for index, candidate in enumerate(candidates):
        candidate['team'] = '我方' if index < (len(candidates) + 1) // 2 else '敌方'

    detail_pairs = []
    pair_pattern = re.compile(r'(\d{1,4})\s*/\s*\d{1,4}')
    for line in lines:
        pairs = pair_pattern.findall(line)
        if len(pairs) >= 4:
            detail_pairs.append([_number(pair[0]) for pair in pairs[:4]])
    for candidate, detail in zip(candidates, detail_pairs):
        candidate['dmg'] = detail[0]
    if not candidates:
        raise ValueError('没有识别到 KDA 数据。请上传同一场比赛的结算总览图和详细表现图。')
    return candidates, '\n'.join(lines)


def editable_players(players):
    frame = pd.DataFrame(players)
    columns = ['name', 'team', 'k', 'd', 'a', 'first', 'dmg', 'acs']
    frame = frame.reindex(columns=columns).fillna(0)
    return st.data_editor(
        frame,
        hide_index=True,
        use_container_width=True,
        num_rows='dynamic',
        column_config={
            'name': '选手名称', 'team': st.column_config.SelectboxColumn('队伍', options=['我方', '敌方']),
            'k': st.column_config.NumberColumn('击杀', min_value=0),
            'd': st.column_config.NumberColumn('死亡', min_value=0),
            'a': st.column_config.NumberColumn('助攻', min_value=0),
            'first': st.column_config.NumberColumn('首杀', min_value=0),
            'dmg': st.column_config.NumberColumn('伤害', min_value=0),
            'acs': st.column_config.NumberColumn('战斗评分', min_value=0),
        },
        key='recognized_players',
    ).to_dict('records')


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
        red_color = '#16b8aa' if red['team'] == '我方' else '#e5484d'
        blue_color = '#16b8aa' if blue['team'] == '我方' else '#e5484d'
        axis.plot(closed_angles, red_values, 'o-', linewidth=2.5, color=red_color, label=red['display_name'])
        axis.fill(closed_angles, red_values, alpha=0.2, color=red_color)
        axis.plot(closed_angles, blue_values, 'o-', linewidth=2.5, color=blue_color, label=blue['display_name'])
        axis.fill(closed_angles, blue_values, alpha=0.2, color=blue_color)
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
st.caption('支持结算截图 OCR，也支持 CSV、JSON 和 Excel。截图识别后可先修改数据，再拖动双方顺序进行对位。')

source = st.radio('数据来源', ['上传截图', '上传 CSV / JSON / Excel'], horizontal=True)
players = None
if source == '上传截图':
    st.info('请上传同一场比赛的两张图：结算总览图和详细表现图。红色识别为敌方，绿色或黄色识别为我方。')
    screenshots = st.file_uploader(
        '上传结算截图（建议同时上传两张）',
        type=['png', 'jpg', 'jpeg', 'webp'],
        accept_multiple_files=True,
    )
    if screenshots and st.button('识别截图数据', type='primary'):
        try:
            recognized, raw_text = extract_screenshot_candidates(screenshots)
            st.session_state['ocr_players'] = recognized
            st.session_state['ocr_text'] = raw_text
        except Exception as error:
            st.error(f'截图识别失败：{error}')
    if 'ocr_players' not in st.session_state:
        st.stop()
    st.subheader('确认或修改识别结果')
    st.caption('OCR 可能误读中文昵称或数字，请重点检查 KDA、伤害和战斗评分。')
    players = editable_players(st.session_state['ocr_players'])
    with st.expander('查看原始 OCR 文本'):
        st.text(st.session_state.get('ocr_text', ''))
else:
    uploaded_file = st.file_uploader('选择选手原始数据文件', type=['csv', 'json', 'xlsx', 'xls'])
    if uploaded_file is None:
        st.info('请先上传 CSV、JSON 或 Excel 文件。')
        st.stop()
    try:
        players = load_players(uploaded_file.name, uploaded_file.getvalue())
    except Exception as error:
        st.error(f'数据读取失败：{error}')
        st.stop()

players = [player for player in players if str(player.get('name', '')).strip()]
red_team = [player for player in players if player['team'] == '我方']
blue_team = [player for player in players if player['team'] == '敌方']
if not red_team or not blue_team:
    st.error('没有识别到完整的我方和敌方数据，请检查 team/队伍 字段。')
    st.stop()
if len(red_team) != 5 or len(blue_team) != 5:
    st.warning(f'当前读取我方 {len(red_team)} 人、敌方 {len(blue_team)} 人，建议双方各 5 人。')

st.subheader('拖动设置对位')
st.caption('把每一方的选手拖动排序；两列中相同序号的选手会进行对位。')

def draggable_team(team, label, key):
    names = [str(player['name']) for player in team]
    if sort_items is None:
        return names
    return sort_items(names, direction='vertical', key=key)


left, right = st.columns(2)
with left:
    st.markdown('#### 我方（绿/黄色）')
    own_order = draggable_team(red_team, '我方', 'own_order')
with right:
    st.markdown('#### 敌方（红色）')
    enemy_order = draggable_team(blue_team, '敌方', 'enemy_order')

own_by_name = {str(player['name']): player for player in red_team}
enemy_by_name = {str(player['name']): player for player in blue_team}
ordered_own = [own_by_name[name] for name in own_order if name in own_by_name]
ordered_enemy = [enemy_by_name[name] for name in enemy_order if name in enemy_by_name]

hero_names = {}
for player in ordered_own + ordered_enemy:
    hero_names[str(player['name'])] = st.text_input(
        f'{player["name"]} 的英雄名称',
        key=f'hero_{player["name"]}',
        placeholder='可选',
    )

if st.button('生成六维对比图', type='primary', use_container_width=True):
    for player in ordered_own + ordered_enemy:
        player['display_name'] = hero_names[str(player['name'])].strip() or str(player['name']).split('#')[0]
    pairings = list(zip(ordered_own, ordered_enemy))
    min_vals, max_vals = prepare_players(ordered_own + ordered_enemy)
    st.pyplot(make_chart(pairings, min_vals, max_vals), clear_figure=True)
    if len(ordered_own) != len(ordered_enemy):
        st.warning('双方人数不同，仅生成前面能够配对的对比图。')
