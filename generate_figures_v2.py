#!/usr/bin/env python3
"""Publication-quality figure generation v2 for JISA submission.

Improvements:
- 9pt base font, 7pt ticks/labels, 8pt legends (print-readable)
- Grayscale-compatible colors with distinct markers
- Optimized for elsarticle single-column width (~8cm)
- Clean layouts, no overlapping elements
- Vector PDF output at 300 DPI
"""
import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FormatStrFormatter
import os

# === Publication-quality settings ===
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 9,
    'axes.labelsize': 9,
    'axes.titlesize': 9,
    'legend.fontsize': 7.5,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
    'lines.linewidth': 1.0,
    'lines.markersize': 4,
    'axes.linewidth': 0.6,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'grid.linewidth': 0.3,
    'axes.grid': True,
    'grid.alpha': 0.3,
})

FIG_DIR = '/home/zq/cyber-range/paper/figures'
os.makedirs(FIG_DIR, exist_ok=True)

# === Color palette: grayscale-safe with distinct hues ===
C = {
    'blue':   '#2166AC',
    'orange': '#D6604D',
    'green':  '#1B7837',
    'purple': '#762A83',
    'red':    '#B2182B',
    'gray':   '#555555',
    'lightblue': '#92C5DE',
    'lightred':  '#F4A582',
    'lightgreen': '#A6DBA0',
}


# ============================================================
# Figure 1: Regret vs sqrt(T) scaling
# ============================================================
def fig_regret():
    data = json.load(open('/home/zq/cyber-range/prototype/regret_scaling_v2.json'))
    fig, ax = plt.subplots(figsize=(4.5, 3.0))

    T_vals = np.array(data['regret_vs_T']['Uniform']['T'])
    sqrt_T = np.sqrt(T_vals)

    styles = [
        ('Uniform', 'o', C['gray'], 'Uniform'),
        ('Weak (PWN-like, I≈0.2)', 's', C['orange'], 'Weak ($I{\\approx}0.2$)'),
        ('Moderate (Web-like, I≈0.8)', '^', C['blue'], 'Moderate ($I{\\approx}0.8$)'),
        ('Strong (Crypto-like, I≈1.6)', 'D', C['green'], 'Strong ($I{\\approx}1.6$)'),
    ]

    for name, marker, color, label in styles:
        regrets = np.array(data['regret_vs_T'][name]['regret'])
        ses = np.array(data['regret_vs_T'][name]['se'])
        ax.errorbar(sqrt_T, regrets, yerr=ses,
                    fmt=marker + '-', color=color, label=label,
                    markersize=4.5, linewidth=1.1, capsize=2, capthick=0.5,
                    markeredgewidth=0.5, markeredgecolor='white')

    ax.set_xlabel(r'$\sqrt{T}$', fontsize=10)
    ax.set_ylabel('Cumulative Bayesian Regret', fontsize=9)
    ax.legend(loc='upper left', framealpha=0.85, edgecolor='#cccccc',
              fontsize=7, ncol=1, handlelength=1.5, borderpad=0.4)
    ax.set_xlim(0, sqrt_T[-1] * 1.03)
    ax.set_ylim(0, None)
    ax.tick_params(axis='both', which='major', pad=2)

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_regret_scaling.pdf', dpi=300, bbox_inches='tight')
    plt.close()
    print('Fig 1: Regret scaling ✓')


# ============================================================
# Figure 2: Phase diagram
# ============================================================
def fig_phase():
    fig, ax = plt.subplots(figsize=(4.5, 3.0))

    T_grid = np.linspace(0, 55, 150)
    R_grid = np.linspace(0, 11, 150)
    TT, RR = np.meshgrid(T_grid, R_grid)
    RT = RR * TT

    Z = np.zeros_like(RT)
    Z[RT < 35] = 0
    Z[(RT >= 35) & (RT < 350)] = 1
    Z[RT >= 350] = 2

    cmap = matplotlib.colors.ListedColormap(['#E8D0D0', '#D0E8D0', '#D0D0E8'])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
    ax.pcolormesh(TT, RR, Z, cmap=cmap, norm=norm, alpha=0.55, shading='auto',
                  rasterized=True)

    # Grid points with observed data
    R_vals = [1, 3, 5, 10]
    T_vals = [3, 5, 10, 20, 30, 50]
    for R in R_vals:
        for T in T_vals:
            ax.plot(T, R, 'o', color='#333333', markersize=3.5,
                    markeredgewidth=0.3, markeredgecolor='white')

    # Regime labels
    ax.text(5, 8.5, 'Regime I\nNoise-Dominated', ha='center', fontsize=7,
            style='italic', color='#8B0000',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFE8E8', edgecolor='#CC9999', alpha=0.9))
    ax.text(20, 6.5, 'Regime II\nPrior-Utility', ha='center', fontsize=7,
            style='italic', color='#006400',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8FFE8', edgecolor='#99CC99', alpha=0.9))
    ax.text(48, 2.5, 'Regime III\nSaturation', ha='center', fontsize=7,
            style='italic', color='#00008B',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8E8FF', edgecolor='#9999CC', alpha=0.9))

    ax.set_xlabel('Search Budget $T$', fontsize=9)
    ax.set_ylabel('Retries $R$', fontsize=9)
    ax.set_xlim(0, 55)
    ax.set_ylim(0, 11)
    ax.set_yticks([1, 3, 5, 10])
    ax.tick_params(axis='both', which='major', pad=2)

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_phase_diagram.pdf', dpi=300, bbox_inches='tight')
    plt.close()
    print('Fig 2: Phase diagram ✓')


# ============================================================
# Figure 3: I_LLM bar chart
# ============================================================
def fig_illm():
    categories = ['Crypto', 'Web', 'Forensics', 'Misc', 'Reverse', 'PWN']
    I_LLM = [1.57, 0.81, 0.65, 0.34, 0.33, 0.16]
    accuracy = [1.0, 1.0, 0.667, 0.667, 0.333, 0.333]
    bar_colors = [C['green'], C['blue'], C['blue'], C['orange'], C['orange'], C['red']]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(5.8, 2.6),
                                    gridspec_kw={'width_ratios': [1.8, 1]})

    # Left: I_LLM bars
    x = np.arange(len(categories))
    bars = ax1.bar(x, I_LLM, color=bar_colors, edgecolor='#333333',
                   linewidth=0.4, width=0.62)
    ax1.axhline(y=0, color='#555555', linewidth=0.5, linestyle='-')
    logK = np.log2(6)
    ax1.axhline(y=logK, color='#888888', linewidth=0.5, linestyle='--')
    ax1.text(5.6, logK, r'$\log_2 K{=}2.58$', fontsize=6.5, va='bottom', color='#666666')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, rotation=20, ha='right', fontsize=7.5)
    ax1.set_ylabel(r'$I_{\rm LLM}$ (bits)', fontsize=9)
    ax1.set_ylim(-1.5, 3.2)
    ax1.tick_params(axis='both', which='major', pad=2)

    for bar, val in zip(bars, I_LLM):
        ypos = val + 0.1 if val >= 0 else val - 0.25
        ax1.text(bar.get_x() + bar.get_width()/2, ypos,
                 f'{val:.2f}', ha='center', fontsize=6.5, fontweight='bold')

    # Right: Accuracy bars
    ax2.bar(x, accuracy, color=bar_colors, edgecolor='#333333',
            linewidth=0.4, width=0.62)
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories, rotation=20, ha='right', fontsize=7.5)
    ax2.set_ylabel('Top-1 Accuracy', fontsize=9)
    ax2.set_ylim(0, 1.15)
    ax2.axhline(y=1/6, color='#888888', linewidth=0.5, linestyle='--')
    ax2.text(5.6, 1/6, 'chance', fontsize=6.5, va='bottom', color='#666666')
    ax2.tick_params(axis='both', which='major', pad=2)

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_illm_bars.pdf', dpi=300, bbox_inches='tight')
    plt.close()
    print('Fig 3: I_LLM bars ✓')


# ============================================================
# Figure 4: Chain amplification
# ============================================================
def fig_chain():
    chain = json.load(open('/home/zq/cyber-range/prototype/chain_depth.json'))
    H_vals = [1, 2, 3, 4, 5]
    T_plot = [10, 20, 30, 50]
    colors = [C['orange'], C['blue'], C['green'], C['purple']]

    fig, ax = plt.subplots(figsize=(4.5, 2.8))

    for idx, T in enumerate(T_plot):
        ratios = []
        for H in H_vals:
            key = f'{H}_{T}'
            if key in chain:
                llm, uni = chain[key]
                ratios.append(llm / max(uni, 0.001))
            else:
                ratios.append(np.nan)
        ax.plot(H_vals, ratios, 'o-', label=f'$T={T}$',
                color=colors[idx], markersize=4.5, linewidth=1.1,
                markeredgewidth=0.4, markeredgecolor='white')

    ax.axhline(y=1.0, color='#888888', linewidth=0.6, linestyle='--')
    ax.set_xlabel('Chain Depth $H$', fontsize=9)
    ax.set_ylabel('LLM / Uniform Success Ratio', fontsize=9)
    ax.set_xticks(H_vals)
    ax.legend(loc='upper left', fontsize=7, framealpha=0.8,
              edgecolor='#cccccc', handlelength=1.5, borderpad=0.3)
    ax.tick_params(axis='both', which='major', pad=2)
    ax.set_ylim(0.85, 1.30)

    # Shade: advantage zone (>1) and disadvantage zone (<1)
    ax.fill_between([0, 6], 1.0, 1.30, alpha=0.04, color='green')
    ax.fill_between([0, 6], 0.85, 1.0, alpha=0.04, color='red')

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_chain_amplification.pdf', dpi=300, bbox_inches='tight')
    plt.close()
    print('Fig 4: Chain amplification ✓')


# ============================================================
# Figure 5: Noise heatmap
# ============================================================
def fig_heatmap():
    noise = json.load(open('/home/zq/cyber-range/prototype/noise_grid.json'))
    pg_vals = sorted(set(float(k.split('_')[0]) for k in noise.keys()))
    pb_vals = sorted(set(float(k.split('_')[1]) for k in noise.keys()))

    advantage = np.zeros((len(pb_vals), len(pg_vals)))
    for i, pb in enumerate(pb_vals):
        for j, pg in enumerate(pg_vals):
            best_adv = -99
            for T in [10, 30, 50]:
                key = f'{pg:.2f}_{pb:.2f}_{T}'
                if key in noise:
                    pl, pu = noise[key]
                    adv = pl - pu
                    if adv > best_adv:
                        best_adv = adv
            advantage[i, j] = best_adv

    fig, ax = plt.subplots(figsize=(4.8, 3.0))

    im = ax.pcolormesh(pg_vals, pb_vals, advantage, cmap='RdBu_r',
                        shading='gouraud', vmin=-0.10, vmax=0.12,
                        rasterized=True)

    X, Y = np.meshgrid(pg_vals, pb_vals)
    cs = ax.contour(X, Y, advantage, levels=[0, 0.05],
                    colors=['#333333', C['green']],
                    linewidths=[1.2, 0.8], linestyles=['-', '--'])
    ax.clabel(cs, fmt='%.2f', fontsize=6.5, inline=True, inline_spacing=3)

    ax.set_xlabel(r'$p_g$ (optimal action success prob.)', fontsize=9)
    ax.set_ylabel(r'$p_b$ (suboptimal action success prob.)', fontsize=9)

    cbar = plt.colorbar(im, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label('LLM $-$ Uniform advantage', fontsize=8)
    cbar.ax.tick_params(labelsize=6.5, pad=1)

    ax.tick_params(axis='both', which='major', pad=2)

    # Annotate sweet spot
    ax.annotate('Prior-utility\nsweet spot',
                xy=(0.47, 0.27), fontsize=6.5, ha='center', color=C['green'],
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.25', facecolor='#E8FFE8',
                          edgecolor=C['green'], alpha=0.85, linewidth=0.5))

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_noise_heatmap.pdf', dpi=300, bbox_inches='tight')
    plt.close()
    print('Fig 5: Noise heatmap ✓')


# ============================================================
# Figure 6: Architecture diagram
# ============================================================
def fig_architecture():
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)
    ax.axis('off')

    layers = [
        (0.3, 6.2, 9.4, 2.4, '#DAE8FC', 'Orchestration Layer'),
        (0.3, 3.8, 9.4, 2.1, '#FFF2CC', 'Intelligence Layer'),
        (0.3, 0.3, 9.4, 3.2, '#D5E8D4', 'Infrastructure Layer'),
    ]

    for x, y, w, h, color, label in layers:
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                                        facecolor=color, edgecolor='#666666',
                                        linewidth=1.2, alpha=0.8)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h + 0.08, label, ha='center', va='bottom',
                fontsize=9.5, fontweight='bold', color='#333333')

    # Orchestration components
    boxes = [
        # x, y, w, h, text, color, fontsize
        (0.6, 6.5, 2.0, 0.8, 'Attack Scripts\n(Python)', '#FFFFFF', 7),
        (2.9, 6.5, 2.0, 0.8, 'TS-MCTS Engine\n(Thompson Sampling)', '#FFFFFF', 7),
        (5.2, 6.5, 2.1, 0.8, 'Scenario Lifecycle\n(Create/Start/Stop)', '#FFFFFF', 7),
        (7.6, 6.5, 1.8, 0.8, 'Docker\nIntegration', '#FFFFFF', 7),
    ]

    # Intelligence components
    boxes += [
        (0.6, 4.1, 2.6, 1.2, 'LLM Gateway\nFastAPI :8000', '#FFFFFF', 7),
        (3.5, 4.1, 2.3, 1.2, 'Endpoints\n/v1/prior\n/v1/attack_plan\n/v1/evaluate', '#FFFFFF', 6.5),
        (6.1, 4.1, 2.5, 1.2, 'MD5 Response Cache\n>90% API cost reduction\nPersistent storage', '#FFFFFF', 6.5),
    ]

    # Infrastructure components
    boxes += [
        (0.6, 0.8, 2.0, 1.2, 'OVS Bridges\n(br-scenario-1,\nbr-scenario-2)', '#FFFFFF', 7),
        (2.9, 0.8, 2.0, 1.2, 'Docker Containers\n(Apache, MySQL,\nSSH, vulnerable apps)', '#FFFFFF', 7),
        (5.2, 0.8, 2.1, 1.2, 'Network Isolation\nPer-scenario subnet\nVLAN/VXLAN', '#FFFFFF', 7),
        (7.6, 0.8, 1.8, 1.2, 'Deploy Script\nbash + ovs-docker\nsingle-command', '#FFFFFF', 7),
    ]

    for x, y, w, h, text, color, fs in boxes:
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                        facecolor=color, edgecolor='#999999',
                                        linewidth=0.7, alpha=0.95)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fs,
                color='#222222', linespacing=1.15)

    # External LLM API
    rect = mpatches.FancyBboxPatch((8.3, 2.8), 1.0, 0.6, boxstyle="round,pad=0.05",
                                    facecolor='#FFFFFF', edgecolor='#999999',
                                    linewidth=0.7, alpha=0.95)
    ax.add_patch(rect)
    ax.text(8.8, 3.1, 'DeepSeek\nV4 Pro API', ha='center', va='center', fontsize=6,
            color='#222222')

    # Arrows with simplified style
    arrow_style = dict(arrowstyle='->', lw=1.0, color='#555555', alpha=0.7)
    ax.annotate('', xy=(1.4, 4.5), xytext=(1.4, 5.2),
                arrowprops=arrow_style)
    ax.text(1.65, 4.85, 'prior', fontsize=6, color='#555555', va='center')

    ax.annotate('', xy=(4.0, 5.2), xytext=(4.0, 4.5),
                arrowprops=arrow_style)
    ax.text(4.25, 4.85, 'feedback', fontsize=6, color='#555555', va='center')

    ax.annotate('', xy=(3.0, 2.0), xytext=(1.8, 2.0),
                arrowprops=dict(arrowstyle='<->', lw=0.8, color='#888888', alpha=0.5))
    ax.text(2.4, 2.2, 'deploy', fontsize=6, color='#888888', ha='center')

    ax.annotate('', xy=(8.8, 2.8), xytext=(3.5, 2.8),
                arrowprops=dict(arrowstyle='<->', lw=0.8, color='#888888',
                               alpha=0.5, connectionstyle='arc3,rad=-0.25'))
    ax.text(6.0, 2.4, 'API calls (cached)', fontsize=6, color='#888888', ha='center')

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_architecture.pdf', dpi=300, bbox_inches='tight')
    plt.close()
    print('Fig 6: Architecture ✓')


def main():
    print('Generating publication-quality figures...\n')
    fig_regret()
    fig_phase()
    fig_illm()
    fig_chain()
    fig_heatmap()
    fig_architecture()
    print(f'\nAll figures saved to {FIG_DIR}/')
    print('Done.')


if __name__ == '__main__':
    main()
