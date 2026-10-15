import io
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

file_path = 'benchmark_data.csv'

def load_and_parse_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    block_1_lines, block_5_lines = [], []
    current_pct = None
    for line in lines:
        cleaned = line.strip().replace(',', '').replace(' ', '')
        if not cleaned:
            continue
        if '1%' in cleaned:
            current_pct = '1%'; continue
        elif '5%' in cleaned:
            current_pct = '5%'; continue
        if 'времявс.' in cleaned or 'времявс' in cleaned:
            continue
        if current_pct == '1%':
            block_1_lines.append(line)
        elif current_pct == '5%':
            block_5_lines.append(line)
    return "".join(block_1_lines), "".join(block_5_lines)

def parse_to_clean_dict(raw_text, pct_label):
    if not raw_text.strip():
        return []
    df = pd.read_csv(io.StringIO(raw_text.strip()))
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df = df[df['граф\\алгоритм'] != 'граф\\алгоритм']
    algo_cols = [c for c in df.columns if c not in ['граф\\алгоритм', 'тип графа']]
    data_list = []
    for _, row in df.iterrows():
        graph_name = row['граф\\алгоритм']
        graph_type = row['тип графа']
        if pd.isna(graph_name) or pd.isna(graph_type):
            continue
        for algo in algo_cols:
            val = str(row[algo]).strip()
            if val == '-' or pd.isna(row[algo]) or val == 'nan':
                continue

            winner = None
            if '(' in val and ')' in val:
                winner = val[val.find('(') + 1:val.find(')')].strip()

            val_clean = val.split('(')[0].strip()
            if '±' in val_clean:
                mean_str, err_str = val_clean.split('±')
                mean_val = float(mean_str.strip())
                err_val = float(err_str.strip())
            else:
                try:
                    mean_val = float(val_clean); err_val = 0.0
                except ValueError:
                    continue
            data_list.append({
                'pct': pct_label, 'graph_type': graph_type,
                'graph_name': graph_name, 'algo': algo,
                'mean': mean_val, 'error': err_val,
                'winner': winner
            })
    return data_list

try:
    raw_data_1, raw_data_5 = load_and_parse_file(file_path)
except FileNotFoundError:
    print(f"Ошибка: Не удалось найти файл '{file_path}'.")
    exit(1)

all_data = parse_to_clean_dict(raw_data_1, '1%') + parse_to_clean_dict(raw_data_5, '5%')
if not all_data:
    print("Ошибка парсинга.")
    exit(1)

df_clean = pd.DataFrame(all_data)
percentages = ['1%', '5%']
graph_types = ['c_alias', 'java', 'rdf']

# ==============================================================================
# ИМЯ ДЛЯ КОЛОНКИ "лучшее (маска)"
# ==============================================================================
best_algo_name = 'лучшее (маска)'

# Победители для 1% / c_alias — берём из данных
winners_1pct_calias = sorted(
    df_clean[
        (df_clean['algo'] == best_algo_name) &
        (df_clean['pct'] == '1%') &
        (df_clean['graph_type'] == 'c_alias')
    ]['winner'].dropna().unique().tolist()
)

if winners_1pct_calias:
    name_1pct_calias = f"multsrc_adv -{', '.join(winners_1pct_calias)}"
else:
    name_1pct_calias = 'multsrc_adv -'

name_default = 'multsrc_adv -ebr'

def get_best_name(pct, g_type):
    if pct == '1%' and g_type == 'c_alias':
        return name_1pct_calias
    return name_default

print(f"Для 1% / c_alias: '{name_1pct_calias}'")
print(f"Для остальных:    '{name_default}'")

# ==============================================================================
# ФИКСИРОВАННЫЙ ПОРЯДОК АЛГОРИТМОВ
# ==============================================================================
ALGO_ORDER_BASE = [
    'multsrc',
    'multsrc_adv',
    'multsrc_adv -e',
    'multsrc_adv -f',
    'multsrc_adv -l',
    'multsrc_adv -r',
    'multsrc_adv -b',
    None,              # ← сюда подставится имя "лучшее" в нужном виде
    'cfpq rsm',
]

def get_algo_order(pct, g_type):
    best_name = get_best_name(pct, g_type)
    return [best_name if a is None else a for a in ALGO_ORDER_BASE]

# ==============================================================================
# СТИЛЬ
# ==============================================================================
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

graph_palette = [
    '#2b5c8f', '#e07b53', '#4a8c5c', '#9b4d8f', '#cca43b',
    '#469ab4', '#c0504d', '#746c70', '#7f9c4e', '#b565a7',
]
graph_markers = ['o', 's', '^', 'D', 'v', 'P', 'X', '*', 'h', '<']

for pct in percentages:
    for g_type in graph_types:
        sub_df = df_clean[(df_clean['pct'] == pct) & (df_clean['graph_type'] == g_type)]
        if sub_df.empty:
            continue

        best_name = get_best_name(pct, g_type)
        algo_order = get_algo_order(pct, g_type)

        # Локально переименовываем колонку "лучшее (маска)" в нужное имя
        sub_df = sub_df.copy()
        sub_df['algo'] = sub_df['algo'].replace({best_algo_name: best_name})

        algos_in_sub = [a for a in algo_order if a in sub_df['algo'].unique()]
        graph_order = list(sub_df['graph_name'].unique())

        graph_style = {
            g: (graph_palette[i % len(graph_palette)],
                graph_markers[i % len(graph_markers)])
            for i, g in enumerate(graph_order)
        }

        fig, ax = plt.subplots(figsize=(11, 5.5), dpi=200)
        ax.set_facecolor('#ffffff')
        fig.patch.set_facecolor('#ffffff')

        x_pos = np.arange(len(algos_in_sub))

        for g_name in graph_order:
            g_df = sub_df[sub_df['graph_name'] == g_name]
            ys, errs = [], []
            for algo in algos_in_sub:
                row = g_df[g_df['algo'] == algo]
                if row.empty:
                    ys.append(np.nan); errs.append(0.0)
                else:
                    ys.append(float(row['mean'].iloc[0]))
                    errs.append(float(row['error'].iloc[0]))

            color, marker = graph_style[g_name]
            ax.plot(
                x_pos, ys,
                color=color, marker=marker,
                markersize=7, linewidth=1.8,
                markerfacecolor='white',
                markeredgecolor=color, markeredgewidth=1.8,
                label=g_name, zorder=3
            )
            if any(e > 0 for e in errs):
                ax.errorbar(
                    x_pos, ys, yerr=errs,
                    fmt='none', ecolor=color,
                    elinewidth=1, capsize=3, capthick=1,
                    alpha=0.55, zorder=2
                )

        ax.set_title(f"Время выполнения по алгоритмам — {g_type} ({pct} вершин)",
                     fontsize=13, fontweight='semibold', color='#222222',
                     pad=18, loc='left')
        ax.set_ylabel("Время выполнения, с", fontsize=10.5, color='#444444', labelpad=10)
        ax.set_xlabel("Алгоритм", fontsize=10.5, color='#444444', labelpad=10)

        ax.grid(axis='y', linestyle='-', color='#eaeaea', linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)

        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        ax.spines['bottom'].set_color('#cccccc')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(algos_in_sub, fontsize=9.5, color='#333333',
                           rotation=20, ha='right')
        ax.tick_params(axis='y', colors='#666666', labelsize=9)

        ax.legend(
            title='Граф', title_fontsize=9,
            frameon=False, fontsize=9.5,
            loc='center left', bbox_to_anchor=(1.02, 0.5),
            labelspacing=0.6
        )

        plt.subplots_adjust(right=0.82)
        plt.tight_layout()

        filename = f"bench_{g_type}_{pct.replace('%', 'pct')}.png"
        plt.savefig(filename, bbox_inches='tight',
                    facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        print(f"Сохранён: {filename}  →  колонка 'лучшее' = '{best_name}'")

print("\nГотово.")