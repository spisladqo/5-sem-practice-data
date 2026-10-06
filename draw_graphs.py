import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Алгоритмы, которые есть в новой таблице
algo_columns = [
    'multsrc_adv',
    'multsrc_adv -e',
    'multsrc_adv -f',
    'multsrc_adv -l',
    'multsrc_adv -r',
    'multsrc_adv -b',
]


def parse_value(val):
    if pd.isna(val):
        return np.nan, np.nan

    s = str(val).strip()
    if s in ['', '-', 'ООМ']:
        return np.nan, np.nan

    if '±' in s:
        parts = s.split('±')
        try:
            mean = float(parts[0].strip())
            std = float(parts[1].strip())
            return mean, std
        except ValueError:
            return np.nan, np.nan
    else:
        try:
            return float(s), 0.0
        except ValueError:
            return np.nan, np.nan


def parse_csv(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip() != '']

    header_indices = [
        i for i, line in enumerate(lines)
        if 'графы \\ алгоритмы' in line
    ]

    data_rows = []

    for h_idx in header_indices:
        header_line = lines[h_idx]
        header_cols = [col.strip() for col in header_line.split(',')]

        algo_indices = []
        for algo in algo_columns:
            found_idx = -1
            norm_algo = algo.replace(' ', '')
            for i, col in enumerate(header_cols):
                if col.replace(' ', '') == norm_algo:
                    found_idx = i
                    break
            algo_indices.append(found_idx)

        for row_idx in range(h_idx + 1, len(lines)):
            if row_idx in header_indices:
                break

            line = lines[row_idx]
            if not line.strip():
                continue

            parts = line.split(',')
            if len(parts) < 3:
                continue

            graph = parts[0].strip()
            if graph == '' or graph.startswith('графы'):
                continue

            try:
                percent = int(parts[1].strip())
            except ValueError:
                continue

            graph_type = parts[2].strip()

            if graph_type == '':
                if graph in ['init', 'arch', 'block', 'crypto', 'drivers', 'mm',
                             'ipc', 'lib', 'security', 'sound', 'fs', 'net']:
                    graph_type = 'c_alias'
                elif graph in ['go_hierarchy', 'go', 'taxonomy_hierarchy']:
                    graph_type = 'rdf'
                else:
                    graph_type = 'java'

            for idx, algo in zip(algo_indices, algo_columns):
                if idx == -1 or idx >= len(parts):
                    mean, std = np.nan, np.nan
                else:
                    mean, std = parse_value(parts[idx])

                data_rows.append({
                    'graph': graph,
                    'graph_type': graph_type,
                    'percent': percent,
                    'algorithm': algo,
                    'mean': mean,
                    'std': std,
                })

    df = pd.DataFrame(data_rows)
    df = df.dropna(subset=['mean'], how='all')
    return df


file_path = '05.10.26 results - Лист1.csv'
df = parse_csv(file_path)

print("Размер DataFrame:", df.shape)
print("Уникальные проценты:", df['percent'].unique())
print("Типы графов:", df['graph_type'].unique())
print("Алгоритмы:", df['algorithm'].unique())

if df.empty:
    print("DataFrame пуст! Проверьте файл.")
    exit()

df['algorithm'] = pd.Categorical(
    df['algorithm'],
    categories=algo_columns,
    ordered=True
)

out_dir = Path('visuals')
out_dir.mkdir(exist_ok=True)

types = df['graph_type'].unique()
percentages = df['percent'].unique()

sns.set_style('whitegrid')
sns.set_palette('husl')

df_avg_std = df.groupby(
    ['graph_type', 'graph', 'percent', 'algorithm'],
    observed=True
).agg({
    'mean': 'mean',
    'std': 'mean'
}).reset_index()

# 1. Точечные графики по типам графов и процентам
#    для java — логарифмическая шкала по Y
for gtype in types:
    for pct in percentages:
        subset = df_avg_std[
            (df_avg_std['graph_type'] == gtype) &
            (df_avg_std['percent'] == pct)
        ].copy()
        if subset.empty:
            continue

        # для лог-шкалы убираем нули и отрицательные значения
        if gtype == 'java':
            subset = subset[subset['mean'] > 0]
            if subset.empty:
                continue

        graphs = subset['graph'].unique()
        plt.figure(figsize=(14, 7))

        for graph in graphs:
            data = subset[subset['graph'] == graph].sort_values('algorithm')
            if data.empty:
                continue

            plt.errorbar(
                x=data['algorithm'].astype(str),
                y=data['mean'],
                yerr=data['std'],
                marker='o',
                capsize=3,
                label=graph,
                linestyle='-',
                linewidth=1
            )

        if gtype == 'java':
            plt.yscale('log')
            plt.grid(True, which='both', linestyle='--', linewidth=0.5)
            ylabel = 'Время (с) – логарифмическая шкала'
            title_extra = ' (log scale)'
        else:
            ylabel = 'Время (с)'
            title_extra = ''

        plt.xticks(rotation=45, ha='right')
        plt.xlabel('Алгоритм')
        plt.ylabel(ylabel)
        plt.title(
            f'{gtype}, {pct}% вершин – сравнение алгоритмов по графам{title_extra}'
        )
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(
            out_dir / f'pointplot_{gtype}_{pct}.png',
            dpi=150,
            bbox_inches='tight'
        )
        plt.close()

# 2. Столбчатые графики по типам графов и процентам
for gtype in types:
    for pct in percentages:
        subset = df_avg_std[
            (df_avg_std['graph_type'] == gtype) &
            (df_avg_std['percent'] == pct)
        ]
        if subset.empty:
            continue

        plt.figure(figsize=(14, 7))
        sns.barplot(
            data=subset,
            x='graph',
            y='mean',
            hue='algorithm',
            palette='Blues_d'
        )
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Время (с)')
        plt.title(f'{gtype}, {pct}% вершин – оптимизированные алгоритмы')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(
            out_dir / f'barplot_{gtype}_{pct}.png',
            dpi=150,
            bbox_inches='tight'
        )
        plt.close()

# 3. Java-графы: только фасетный столбчатый график с логарифмической шкалой
#    (точечный java-график уже построен выше с лог-шкалой)
java_avg_std = df_avg_std[df_avg_std['graph_type'] == 'java']

if not java_avg_std.empty:
    for pct in java_avg_std['percent'].unique():
        subset = java_avg_std[java_avg_std['percent'] == pct].copy()
        subset = subset[subset['mean'] > 0]
        if subset.empty:
            continue

        graphs = subset['graph'].unique()
        n_graphs = len(graphs)
        cols = 4
        rows = (n_graphs + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(16, 4 * rows))
        if n_graphs == 1:
            axes = [axes]
        else:
            axes = axes.flatten()

        for i, graph in enumerate(graphs):
            data = subset[subset['graph'] == graph].sort_values('algorithm')
            ax = axes[i]
            sns.barplot(data=data, x='algorithm', y='mean', ax=ax, palette='Blues_d')
            ax.set_yscale('log')
            ax.set_title(graph, fontsize=10)
            ax.set_xlabel('')
            ax.set_ylabel('Время (с)')
            ax.tick_params(axis='x', rotation=45, labelsize=8)

        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])

        plt.suptitle(
            f'Java-графы, {pct}% вершин – столбцы (логарифмическая шкала)',
            fontsize=16
        )
        plt.tight_layout()
        plt.savefig(
            out_dir / f'java_barlog_facet_{pct}.png',
            dpi=150,
            bbox_inches='tight'
        )
        plt.close()

print(f"Все графики сохранены в папку '{out_dir}/'")
print("Уникальные проценты в итоговом DataFrame:", df['percent'].unique())