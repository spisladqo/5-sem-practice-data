import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
from pathlib import Path

algo_columns = ['multsrc', 'multsrc_adv', 'multsrc_adv -e', 'multsrc_adv -f',
                'multsrc_adv -l', 'multsrc_adv w',
                'multsrc_adv -b', 'multsrc_adv -elbfw']

def parse_value(val):
    if pd.isna(val) or val.strip() in ['', '-']:
        return np.nan, np.nan
    if '±' in s:
        parts = s.split('±')
        mean = float(parts[0].strip())
        std = float(parts[1].strip())
        return mean, std
    else:
        try:
            return float(s.strip()), 0.0
        except:
            return np.nan, np.nan

def parse_csv(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip() != '']

    header_indices = [i for i, line in enumerate(lines) if 'графы \\ алгоритмы' in line]
    data_rows = []

    for h_idx in header_indices:
        header_line = lines[h_idx]
        header_cols = [col.strip() for col in header_line.split(',')]
        algo_indices = []
        for algo in algo_columns:
            found = False
            for i, col in enumerate(header_cols):
                if algo.replace(' ', '') in col.replace(' ', ''):
                    algo_indices.append(i)
                    found = True
                    break
            if not found:
                algo_indices.append(-1)

        for row_idx in range(h_idx + 1, len(lines)):
            if row_idx in header_indices:
                break
            line = lines[row_idx]
            if line == '':
                continue
            parts = line.split(',')
            if len(parts) < 5:
                continue
            graph = parts[0].strip()
            if graph.startswith('note:') or graph.startswith('"note:'):
                continue
            if graph == '':
                continue
            try:
                percent = int(parts[2].strip())
                sample = int(parts[3].strip())
            except ValueError:
                continue
            if len(parts) >= 5:
                graph_type = parts[4].strip()
            else:
                graph_type = 'unknown'
            if graph_type == '':
                if graph in ['init', 'arch', 'block', 'crypto', 'drivers', 'mm', 'ipc', 'lib', 'security', 'sound', 'fs', 'net']:
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
                    'sample': sample,
                    'algorithm': algo,
                    'mean': mean,
                    'std': std
                })

    df = pd.DataFrame(data_rows)
    df = df.dropna(subset=['mean'], how='all')
    return df

file_path = 'result.csv'
df = parse_csv(file_path)
print("Размер DataFrame:", df.shape)
print("Уникальные проценты:", df['percent'].unique())
print("Уникальные выборки:", df['sample'].unique())
print("Типы графов:", df['graph_type'].unique())

if df.empty:
    print("DataFrame пуст! Проверьте файл.")
    exit()

df['algorithm'] = pd.Categorical(df['algorithm'], categories=algo_columns, ordered=True)

out_dir = Path('visuals')
out_dir.mkdir(exist_ok=True)

types = df['graph_type'].unique()
percentages = df['percent'].unique()

sns.set_style('whitegrid')
sns.set_palette('husl')

df_avg_std = df.groupby(['graph_type', 'graph', 'percent', 'algorithm'], observed=True).agg({
    'mean': 'mean',
    'std': 'mean'
}).reset_index()

for gtype in types:
    for pct in percentages:
        subset = df_avg_std[(df_avg_std['graph_type'] == gtype) & (df_avg_std['percent'] == pct)]
        if subset.empty:
            continue
        graphs = subset['graph'].unique()
        plt.figure(figsize=(14, 7))
        for graph in graphs:
            data = subset[subset['graph'] == graph].sort_values('algorithm')
            if data.empty:
                continue
            plt.errorbar(x=data['algorithm'].astype(str), y=data['mean'],
                         yerr=data['std'], marker='o', capsize=3, label=graph, linestyle='-', linewidth=1)
        plt.xticks(rotation=45, ha='right')
        plt.xlabel('Алгоритм')
        plt.ylabel('Время (с)')
        plt.title(f'{gtype}, {pct}% вершин – сравнение алгоритмов по графам')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(out_dir / f'pointplot_{gtype}_{pct}.png', dpi=150, bbox_inches='tight')
        plt.close()

color_multsrc = '#D95F5F'      # приглушённый красный
color_multsrc_adv = '#5B8DB8'  # приглушённый синий

for gtype in types:
    for pct in percentages:
        subset = df_avg_std[(df_avg_std['graph_type'] == gtype) & (df_avg_std['percent'] == pct)]
        multsrc = subset[subset['algorithm'] == 'multsrc']
        adv = subset[subset['algorithm'] == 'multsrc_adv']
        if multsrc.empty or adv.empty:
            continue
        graphs = multsrc.groupby('graph')['mean'].mean().sort_values().index
        x = np.arange(len(graphs))
        width = 0.35
        fig, ax = plt.subplots(figsize=(14, 8))
        m_means = [multsrc[multsrc['graph']==g]['mean'].values[0] for g in graphs]
        m_stds  = [multsrc[multsrc['graph']==g]['std'].values[0] for g in graphs]
        a_means = [adv[adv['graph']==g]['mean'].values[0] for g in graphs]
        a_stds  = [adv[adv['graph']==g]['std'].values[0] for g in graphs]
        ax.bar(x - width/2, m_means, width, yerr=m_stds,
               label='multsrc', color=color_multsrc, capsize=3, error_kw={'ecolor': 'black'})
        ax.bar(x + width/2, a_means, width, yerr=a_stds,
               label='multsrc_adv', color=color_multsrc_adv, capsize=3, error_kw={'ecolor': 'black'})
        if gtype == 'java':
            ax.set_yscale('log')
            ylabel = 'Время (с) – логарифмическая шкала'
        else:
            ylabel = 'Время (с)'
        ax.set_xticks(x)
        ax.set_xticklabels(graphs, rotation=45, ha='right')
        ax.set_ylabel(ylabel)
        ax.set_title(f'{gtype}, {pct}% вершин – сравнение multsrc и multsrc_adv')
        ax.legend()
        plt.tight_layout()
        plt.savefig(out_dir / f'multsrc_vs_adv_{gtype}_{pct}.png', dpi=150, bbox_inches='tight')
        plt.close()

allowed_graphs_by_type = {
    'c_alias': ['arch', 'crypto', 'drivers', 'fs', 'init', 'ipc', 'net', 'security'],
    'java': ['avrora', 'batik', 'commons_io', 'commons_lang3', 'fop',
             'mockito', 'sunflow', 'tomcat'],
}

for gtype in types:
    for pct in percentages:
        subset = df_avg_std[(df_avg_std['graph_type'] == gtype) & (df_avg_std['percent'] == pct)]
        others = subset[subset['algorithm'] != 'multsrc']
        if others.empty:
            continue
        # Фильтруем графы, если для данного типа задан список
        if gtype in allowed_graphs_by_type:
            allowed = allowed_graphs_by_type[gtype]
            others = others[others['graph'].isin(allowed)]
            if others.empty:
                continue
            # Сортируем в порядке, заданном в списке
            others['graph'] = pd.Categorical(others['graph'], categories=allowed, ordered=True)
            others = others.sort_values('graph')
        plt.figure(figsize=(14, 7))
        sns.barplot(data=others, x='graph', y='mean', hue='algorithm', palette='Blues_d')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Время (с)')
        plt.title(f'{gtype}, {pct}% вершин – оптимизированные алгоритмы (кроме multsrc)')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(out_dir / f'others_{gtype}_{pct}.png', dpi=150, bbox_inches='tight')
        plt.close()

java_df = df[df['graph_type'] == 'java']
if not java_df.empty:
    java_avg = java_df.groupby(['graph', 'percent', 'algorithm'], observed=True)['mean'].mean().reset_index()
    java_std = java_df.groupby(['graph', 'percent', 'algorithm'], observed=True)['std'].mean().reset_index()
    java_avg_std = java_avg.merge(java_std, on=['graph', 'percent', 'algorithm'], suffixes=('', '_std'))

    for pct in java_avg_std['percent'].unique():
        subset = java_avg_std[java_avg_std['percent'] == pct]
        subset = subset[subset['mean'] > 0]
        if subset.empty:
            continue
        plt.figure(figsize=(16, 8))
        graphs = subset['graph'].unique()
        for graph in graphs:
            data = subset[subset['graph'] == graph].sort_values('algorithm')
            if data.empty:
                continue
            plt.errorbar(x=data['algorithm'].astype(str), y=data['mean'],
                         yerr=data['std'], marker='o', capsize=3, label=graph,
                         linestyle='-', linewidth=1.5, alpha=0.8)
        plt.yscale('log')
        plt.xticks(rotation=45, ha='right')
        plt.xlabel('Алгоритм')
        plt.ylabel('Время (с) – логарифмическая шкала')
        plt.title(f'Java-графы, {pct}% вершин – все алгоритмы (log scale, точки)')
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(out_dir / f'java_logscale_points_{pct}.png', dpi=150, bbox_inches='tight')
        plt.close()

if not java_df.empty:
    for pct in java_avg_std['percent'].unique():
        subset = java_avg_std[java_avg_std['percent'] == pct]
        subset = subset[subset['mean'] > 0]
        if subset.empty:
            continue
        graphs = subset['graph'].unique()
        n_graphs = len(graphs)
        cols = 4
        rows = (n_graphs + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(16, 4*rows))
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
        for j in range(i+1, len(axes)):
            fig.delaxes(axes[j])
        plt.suptitle(f'Java-графы, {pct}% вершин – столбцы (логарифмическая шкала)', fontsize=16)
        plt.tight_layout()
        plt.savefig(out_dir / f'java_barlog_facet_{pct}.png', dpi=150, bbox_inches='tight')
        plt.close()

print(f"Все графики сохранены в папку '{out_dir}/'")
print("Уникальные проценты в итоговом DataFrame:", df['percent'].unique())