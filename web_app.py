import csv
import io
import json
import re
from pathlib import Path
from urllib.request import urlopen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
from matplotlib import font_manager
from matplotlib.offsetbox import AnnotationBbox, OffsetImage


def configure_chinese_font():
    font_paths = [
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        Path('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf'),
        Path('C:/Windows/Fonts/NotoSansSC-VF.ttf'),
        Path('C:/Windows/Fonts/msyh.ttc'),
        Path('C:/Windows/Fonts/simhei.ttf'),
    ]
    for font_path in font_paths:
        if font_path.exists():
            font_manager.fontManager.addfont(str(font_path))
            font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
            plt.rcParams['font.sans-serif'] = [font_name]
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['axes.unicode_minus'] = False
            return

    font_candidates = [
        'Noto Sans CJK SC', 'Noto Sans CJK JP', 'Noto Sans SC', 'Microsoft YaHei',
        'SimHei', 'DengXian', 'Arial Unicode MS',
    ]
    installed_fonts = {font.name for font in font_manager.fontManager.ttflist}
    selected_font = next((font for font in font_candidates if font in installed_fonts), None)
    if selected_font:
        plt.rcParams['font.sans-serif'] = [selected_font, 'DejaVu Sans']
    else:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False


configure_chinese_font()


AGENT_NAMES = [
    '请选择英雄', '炼狱 Brimstone', '不死鸟 Phoenix', '贤者 Sage', '捷风 Jett',
    '雷兹 Raze', '幽影 Omen', '毒蛇 Viper', '零 Cypher', '猎枭 Sova',
    '芮娜 Reyna', '奇乐 Killjoy', '铁臂 Breach', '盖可 Gekko', '霓虹 Neon',
    '星礈 Astra', 'KAY/O', '海神 Harbor', '黑梦 Fade', '斯凯 Skye',
    '尚勃勒 Chamber', '夜露 Yoru', '壹决 Iso', '钛狐 Clove', '维斯 Vyse',
    '钢索 Deadlock', '图伊 Tejo', 'Waylay', '迷核 Miks', '暮蝶 Veto',
]
AGENT_API_NAMES = {name.split()[-1]: name for name in AGENT_NAMES if name != '请选择英雄'}


@st.cache_data(show_spinner=False)
def load_agent_icons():
    try:
        with urlopen('https://valorant-api.com/v1/agents?isPlayableCharacter=true', timeout=8) as response:
            payload = json.loads(response.read().decode('utf-8'))
        return {
            item['displayName']: item['displayIcon']
            for item in payload.get('data', [])
            if item.get('displayName') and item.get('displayIcon')
        }
    except Exception:
        return {}


def agent_key(label):
    return label.split()[-1] if label else ''


def agent_icon(label, icons):
    if not label or label == '请选择英雄':
        return None
    english_name = agent_key(label)
    return next((url for name, url in icons.items() if name.lower() == english_name.lower()), None)


@st.cache_data(show_spinner=False)
def load_agent_image(url):
    if not url:
        return None
    try:
        with urlopen(url, timeout=8) as response:
            return Image.open(io.BytesIO(response.read())).convert('RGBA')
    except Exception:
        return None

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


def _ocr_positioned_lines(image):
    if pytesseract is None:
        raise ValueError('截图识别依赖尚未安装，请重新部署应用后再试')
    data = pytesseract.image_to_data(
        image,
        lang='chi_sim+eng',
        config='--psm 11',
        output_type=pytesseract.Output.DICT,
    )
    words = []
    for index, text in enumerate(data['text']):
        text = text.strip()
        if not text:
            continue
        try:
            confidence = float(data['conf'][index])
        except (TypeError, ValueError):
            confidence = -1
        if confidence >= 0:
            words.append((int(data['top'][index]), int(data['left'][index]), text))
    words.sort()
    lines = []
    for top, left, text in words:
        if not lines or top - lines[-1]['top'] > 22:
            lines.append({'top': top, 'bottom': top + 30, 'words': [(left, text)]})
        else:
            line = lines[-1]
            line['bottom'] = max(line['bottom'], top + 30)
            line['words'].append((left, text))
    for line in lines:
        line['words'].sort()
        line['text'] = ' '.join(text for _, text in line['words'])
    return lines


def _number(value):
    try:
        return float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        return 0.0


def extract_screenshot_candidates(uploaded_files):
    kda_pattern = re.compile(r'(\d{1,2})\s*[/:|丨]\s*(\d{1,2})\s*[/:|丨]\s*(\d{1,2})')
    pair_pattern = re.compile(r'(\d{1,4})\s*/\s*(\d{1,4})')
    name_pattern = re.compile(r'([A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff_]{0,24}[#＃]\s*\d{3,6})')
    all_candidates = []
    raw_texts = []

    for uploaded_file, team in uploaded_files:
        image = Image.open(io.BytesIO(uploaded_file.getvalue())).convert('RGB')
        positioned_lines = _ocr_positioned_lines(image)
        lines = [line['text'] for line in positioned_lines]
        raw_texts.append(f'[{uploaded_file.name} / {team} / position-anchored]\n' + '\n'.join(lines))
        occurrences = []
        for line_index, line in enumerate(lines):
            match = kda_pattern.search(line)
            if match:
                occurrences.append((line_index, match))
        if len(occurrences) < 5:
            raise ValueError(f'{uploaded_file.name} 未定位到至少 5 条 KDA 数据')
        selected_occurrences = occurrences[:5] if team == '我方' else occurrences[-5:]
        for index, (line_index, kda_match) in enumerate(selected_occurrences):
            next_index = next(
                (other_index for other_index, _ in occurrences if other_index > line_index),
                len(lines),
            )
            block_lines = lines[line_index:next_index]
            block_text = ' '.join(block_lines)
            after_kda = block_text[kda_match.end():]
            stats = tuple(_number(value) for value in kda_match.groups())
            normalized_block = re.sub(r'(?<=[A-Za-z\u4e00-\u9fff0-9_])\s+(?=[A-Za-z\u4e00-\u9fff0-9_#])', '', block_text)
            name_matches = name_pattern.findall(normalized_block)
            name = name_matches[-1].replace('＃', '#') if name_matches else ''
            if name:
                first_cjk = re.search(r'[\u4e00-\u9fff]', name)
                if first_cjk:
                    name = name[first_cjk.start():]
            score_values = re.findall(r'(?<![/\d])([1-5]\d{2})(?![/\d])', after_kda)
            candidate = {
                'name': name or f'待确认选手{index + 1}',
                'team': team, 'k': stats[0], 'd': stats[1], 'a': stats[2],
                'first': 0, 'dmg': 0, 'acs': _number(score_values[0]) if score_values else 0,
            }
            first_match = re.search(r'首\s*杀[^\d]{0,12}([0-5])', after_kda)
            if first_match:
                candidate['first'] = _number(first_match.group(1))
            pair_matches = list(pair_pattern.finditer(after_kda))
            damage_match = next((match for match in pair_matches if _number(match.group(1)) >= 50), None)
            damage_label = re.search(r'(?:回合|相合|回|合)\s*伤害[^\d]{0,12}(\d{2,3})', after_kda)
            if damage_label:
                candidate['dmg'] = _number(damage_label.group(1))
            elif damage_match:
                candidate['dmg'] = _number(damage_match.group(1))
            if not first_match:
                damage_line_index = next(
                    (line_index for line_index, line in enumerate(block_lines)
                     if re.search(r'(?:回合|相合|回|合)\s*伤害', line)),
                    None,
                )
                if damage_line_index is None and damage_match:
                    damage_line_index = next(
                        (line_index for line_index, line in enumerate(block_lines)
                         if damage_match.group(0) in line),
                        None,
                    )
                if damage_line_index is not None:
                    preceding_lines = block_lines[max(0, damage_line_index - 4):damage_line_index]
                    preceding_numbers = []
                    for preceding_line in preceding_lines:
                        preceding_numbers.extend(re.findall(r'(?<![/\d])([0-5])(?![/\d])', preceding_line))
                    if preceding_numbers:
                        candidate['first'] = _number(preceding_numbers[-1])
            all_candidates.append(candidate)

    if not all_candidates:
        raise ValueError('没有识别到 KDA 数据。请确认上传的是包含选手 KDA 的结算截图。')
    return all_candidates, '\n\n'.join(raw_texts)


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
        axis.legend(loc='upper right', bbox_to_anchor=(1.08, 1.0), fontsize=8)
    for axis in axes_flat[len(pairings):]:
        axis.axis('off')
    figure.suptitle('无畏契约对位雷达图', fontsize=19, fontweight='bold')
    figure.tight_layout(rect=(0.06, 0.02, 0.94, 0.94))
    for index, (red, blue) in enumerate(pairings):
        axis_position = axes_flat[index].get_position()
        for x_position, player in ((axis_position.x0 - 0.035, red), (axis_position.x1 + 0.035, blue)):
            avatar = load_agent_image(player.get('icon_url'))
            if avatar is not None:
                figure.add_artist(AnnotationBbox(
                    OffsetImage(avatar, zoom=0.12),
                    (x_position, axis_position.y0 + axis_position.height / 2),
                    xycoords=figure.transFigure,
                    frameon=True,
                    bboxprops={'boxstyle': 'round,pad=0.25', 'fc': 'white', 'ec': '#d8dee8'},
                ))
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
    st.info('请分别上传两张同一场比赛的详情截图，并明确选择每张图属于我方还是敌方。程序会读取该图中展开的 5 名选手。')
    left_upload, right_upload = st.columns(2)
    with left_upload:
        own_screenshot = st.file_uploader('上传一方详情截图', type=['png', 'jpg', 'jpeg', 'webp'], key='own_screenshot')
        own_team = st.selectbox('这张图的队伍', ['我方', '敌方'], key='own_team')
    with right_upload:
        enemy_screenshot = st.file_uploader('上传另一方详情截图', type=['png', 'jpg', 'jpeg', 'webp'], key='enemy_screenshot')
        enemy_team = st.selectbox('这张图的队伍', ['敌方', '我方'], key='enemy_team')
    screenshot_inputs = []
    if own_screenshot:
        screenshot_inputs.append((own_screenshot, own_team))
    if enemy_screenshot:
        screenshot_inputs.append((enemy_screenshot, enemy_team))
    if screenshot_inputs and st.button('识别截图数据', type='primary'):
        try:
            recognized, raw_text = extract_screenshot_candidates(screenshot_inputs)
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
st.caption('先为选手选择英雄，再拖动头像排序；两列中相同序号的英雄会进行对位。')

agent_icons = load_agent_icons()
hero_names = {}
for player in players:
    player_name = str(player['name'])
    hero_names[player_name] = st.selectbox(
        f'{player_name} 的英雄',
        AGENT_NAMES,
        format_func=lambda label: label,
        key=f'hero_{player_name}',
    )

def draggable_team(team, label, key):
    names = [f'{hero_names.get(str(player["name"]), "请选择英雄")}  ·  {player["name"]}' for player in team]
    if sort_items is None:
        return names
    return sort_items(names, direction='vertical', key=key)


left, right = st.columns(2)
with left:
    st.markdown('#### 我方（绿/黄色）')
    own_preview = st.columns(len(red_team))
    for index, player in enumerate(red_team):
        icon_url = agent_icon(hero_names.get(str(player['name'])), agent_icons)
        if icon_url:
            own_preview[index].image(icon_url, width=52)
        own_preview[index].caption(hero_names.get(str(player['name']), '请选择英雄'))
    own_order = draggable_team(red_team, '我方', 'own_order')
with right:
    st.markdown('#### 敌方（红色）')
    enemy_preview = st.columns(len(blue_team))
    for index, player in enumerate(blue_team):
        icon_url = agent_icon(hero_names.get(str(player['name'])), agent_icons)
        if icon_url:
            enemy_preview[index].image(icon_url, width=52)
        enemy_preview[index].caption(hero_names.get(str(player['name']), '请选择英雄'))
    enemy_order = draggable_team(blue_team, '敌方', 'enemy_order')

own_by_name = {str(player['name']): player for player in red_team}
enemy_by_name = {str(player['name']): player for player in blue_team}
ordered_own = [own_by_name[item.split('  ·  ', 1)[1]] for item in own_order if len(item.split('  ·  ', 1)) == 2 and item.split('  ·  ', 1)[1] in own_by_name]
ordered_enemy = [enemy_by_name[item.split('  ·  ', 1)[1]] for item in enemy_order if len(item.split('  ·  ', 1)) == 2 and item.split('  ·  ', 1)[1] in enemy_by_name]

st.subheader('对位头像（随拖动顺序更新）')
avatar_columns = st.columns(max(len(ordered_own), len(ordered_enemy), 1))
for index, column in enumerate(avatar_columns):
    with column:
        for team_players in (ordered_own, ordered_enemy):
            if index < len(team_players):
                player = team_players[index]
                icon_url = agent_icon(hero_names.get(str(player['name'])), agent_icons)
                if icon_url:
                    st.image(icon_url, width=58)
                else:
                    st.caption(hero_names.get(str(player['name']), '请选择英雄'))

if st.button('生成六维对比图', type='primary', use_container_width=True):
    for player in ordered_own + ordered_enemy:
        player['display_name'] = hero_names.get(str(player['name']), '请选择英雄')
        player['icon_url'] = agent_icon(player['display_name'], agent_icons)
    pairings = list(zip(ordered_own, ordered_enemy))
    min_vals, max_vals = prepare_players(ordered_own + ordered_enemy)
    st.pyplot(make_chart(pairings, min_vals, max_vals), clear_figure=True)
    if len(ordered_own) != len(ordered_enemy):
        st.warning('双方人数不同，仅生成前面能够配对的对比图。')
