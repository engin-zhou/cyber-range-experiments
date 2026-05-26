#!/usr/bin/env python3
"""Nature-figure quality redraw of all 5 data figures.

Follows nature-figure skill conventions:
- PALETTE from api.md
- Figure contract before each plot
- 300 DPI, serif fonts, clean layouts
"""
import numpy as np, json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.gridspec import GridSpec

# === Nature-figure PALETTE ===
P = {
    "blue_main":      "#0F4D92",
    "blue_secondary": "#3775BA",
    "green_1": "#DDF3DE",
    "green_2": "#AADCA9",
    "green_3": "#8BCF8B",
    "red_1":   "#F6CFCB",
    "red_2":   "#E9A6A1",
    "red_strong": "#B64342",
    "neutral_light": "#CFCECE",
    "neutral_mid":   "#767676",
    "neutral_dark":  "#4D4D4D",
    "neutral_black": "#272727",
    "gold":   "#FFD700",
    "teal":   "#42949E",
    "violet": "#9A4D8E",
    "magenta":"#EA84DD",
}

METHOD_COLORS = {
    'uniform': P["neutral_mid"],
    'weak':    P["red_strong"],
    'moderate': P["blue_main"],
    'strong':  P["teal"],
}

# === Global style ===
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 9,
    'axes.labelsize': 10,
    'axes.titlesize': 10,
    'legend.fontsize': 8.5,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'axes.linewidth': 0.6,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'xtick.major.pad': 3,
    'ytick.major.pad': 3,
    'lines.linewidth': 1.2,
    'lines.markersize': 4.5,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.03,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

FIG_DIR = '/home/zq/cyber-range/paper/figures'
os.makedirs(FIG_DIR, exist_ok=True)

DATA_DIR = '/home/zq/cyber-range/prototype'


# ============================================================
# Figure 1: Regret vs sqrt(T) — contract: "Higher I_LLM reduces regret slope"
# ============================================================
def fig_regret():
    """
    Core conclusion: Stronger LLM priors produce shallower regret slopes.
    Evidence: sqrt(T) linear fits with R^2 > 0.987.
    """
    data = json.load(open(f'{DATA_DIR}/regret_scaling_v2.json'))
    T_vals = np.array(data['regret_vs_T']['Uniform']['T'])
    sqrt_T = np.sqrt(T_vals)

    fig, ax = plt.subplots(figsize=(5.0, 3.3))

    styles = [
        ('Uniform',  'o', P["neutral_mid"],  'Uniform', 0.7),
        ('Weak (PWN-like, I≈0.2)',    's', P["red_strong"], 'Weak ($I{\\approx}0.2$)', 0.85),
        ('Moderate (Web-like, I≈0.8)', '^', P["blue_main"], 'Moderate ($I{\\approx}0.8$)', 0.85),
        ('Strong (Crypto-like, I≈1.6)','D', P["teal"], 'Strong ($I{\\approx}1.6$)', 0.85),
    ]

    for name, marker, color, label, alpha in styles:
        regrets = np.array(data['regret_vs_T'][name]['regret'])
        ses = np.array(data['regret_vs_T'][name]['se'])
        ax.errorbar(sqrt_T, regrets, yerr=ses, fmt=marker+'-',
                    color=color, label=label, markersize=5,
                    linewidth=1.3, capsize=2.5, capthick=0.6,
                    markeredgewidth=0.4, markeredgecolor='white',
                    alpha=alpha)

        # Fit line
        fit = np.polyfit(sqrt_T, regrets, 1)
        ax.plot(sqrt_T, fit[0]*sqrt_T + fit[1], '--', color=color,
                linewidth=0.7, alpha=0.4)

    ax.set_xlabel(r'$\sqrt{T}$', fontsize=11)
    ax.set_ylabel('Cumulative Bayesian Regret', fontsize=10)
    ax.legend(loc='upper left', frameon=True, edgecolor=P["neutral_light"],
              framealpha=0.9, fontsize=7.5, handlelength=1.5)
    ax.set_xlim(0, sqrt_T[-1]*1.03)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f'))

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_regret_scaling.pdf', dpi=300)
    plt.close()
    print('Fig 1: Regret scaling ✓')


# ============================================================
# Figure 2: Phase diagram — contract: "Three regimes partition the (T,R) space"
# ============================================================
def fig_phase():
    fig, ax = plt.subplots(figsize=(5.0, 3.2))

    T_grid = np.linspace(0, 55, 80)
    R_grid = np.linspace(0, 11, 80)
    TT, RR = np.meshgrid(T_grid, R_grid)
    RT = RR * TT

    Z = np.zeros_like(RT)
    Z[RT < 35] = 0
    Z[(RT >= 35) & (RT < 350)] = 1
    Z[RT >= 350] = 2

    cmap = matplotlib.colors.ListedColormap([
        P["red_1"],   # Regime I - light red
        P["green_1"], # Regime II - light green
        P["blue_secondary"] + "30",  # Regime III - very light blue
    ])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
    ax.pcolormesh(TT, RR, Z, cmap=cmap, norm=norm, alpha=0.6, shading='auto')

    # Grid markers
    for R in [1, 3, 5, 10]:
        for T in [3, 5, 10, 20, 30, 50]:
            ax.plot(T, R, 'o', color=P["neutral_dark"], markersize=2.5,
                    markeredgewidth=0)

    # Regime labels
    label_style = dict(fontsize=7.5, ha='center', fontstyle='italic')
    ax.text(5, 8.5, 'Regime I\nNoise-Dominated', **label_style,
            color=P["red_strong"],
            bbox=dict(boxstyle='round,pad=0.3', fc=P["red_1"], ec=P["red_2"], alpha=0.9))
    ax.text(20, 6.5, 'Regime II\nPrior-Utility', **label_style,
            color=P["teal"],
            bbox=dict(boxstyle='round,pad=0.3', fc=P["green_1"], ec=P["green_3"], alpha=0.9))
    ax.text(48, 2.5, 'Regime III\nSaturation', **label_style,
            color=P["blue_main"],
            bbox=dict(boxstyle='round,pad=0.3', fc='#E8F0FF', ec=P["blue_secondary"], alpha=0.9))

    ax.set_xlabel('Search Budget $T$', fontsize=10)
    ax.set_ylabel('Retries $R$', fontsize=10)
    ax.set_xlim(0, 55)
    ax.set_ylim(0, 11)
    ax.set_yticks([1, 3, 5, 10])

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_phase_diagram.pdf', dpi=300)
    plt.close()
    print('Fig 2: Phase diagram ✓')


# ============================================================
# Figure 3: I_LLM bars — contract: "LLM prior quality varies 10x across categories"
# ============================================================
def fig_illm():
    categories = ['Crypto', 'Web', 'Forensics', 'Misc', 'Reverse', 'PWN']
    I_LLM_vals = [1.57, 0.81, 0.65, 0.34, 0.33, 0.16]
    accuracy_vals = [1.0, 1.0, 2/3, 2/3, 1/3, 1/3]
    bar_colors = [P["teal"], P["blue_main"], P["blue_main"],
                  P["red_strong"], P["red_strong"], P["red_strong"]]

    fig = plt.figure(figsize=(5.5, 2.8))
    gs = GridSpec(1, 2, width_ratios=[2, 1], wspace=0.35)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    # Left: I_LLM
    x = np.arange(len(categories))
    bars = ax1.bar(x, I_LLM_vals, color=bar_colors, edgecolor='white',
                   linewidth=0.3, width=0.6)
    ax1.axhline(y=0, color=P["neutral_mid"], linewidth=0.6, linestyle='-')
    logK = np.log2(6)
    ax1.axhline(y=logK, color=P["neutral_light"], linewidth=0.6, linestyle='--')
    ax1.text(5.4, logK, r'$\log_2 K\,{=}\,2.58$', fontsize=7, va='bottom', color=P["neutral_mid"])
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, rotation=20, ha='right', fontsize=8)
    ax1.set_ylabel(r'$I_{\mathrm{LLM}}$ (bits)', fontsize=10)
    ax1.set_ylim(-1.6, 3.2)
    ax1.grid(axis='y', alpha=0.2, linewidth=0.3)

    for bar, val in zip(bars, I_LLM_vals):
        ypos = val + 0.12 if val >= 0 else val - 0.3
        ax1.text(bar.get_x() + bar.get_width()/2, ypos, f'{val:.2f}',
                 ha='center', fontsize=7, fontweight='bold', color=P["neutral_dark"])

    # Right: Accuracy
    ax2.bar(x, accuracy_vals, color=bar_colors, edgecolor='white',
            linewidth=0.3, width=0.6)
    ax2.axhline(y=1/6, color=P["neutral_light"], linewidth=0.6, linestyle='--')
    ax2.text(5.4, 1/6, 'chance', fontsize=7, va='bottom', color=P["neutral_mid"])
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories, rotation=20, ha='right', fontsize=8)
    ax2.set_ylabel('Top-1 Accuracy', fontsize=10)
    ax2.set_ylim(0, 1.12)
    ax2.grid(axis='y', alpha=0.2, linewidth=0.3)

    fig.tight_layout()
    fig.savefig(f'{FIG_DIR}/fig_illm_bars.pdf', dpi=300)
    plt.close(fig)
    print('Fig 3: I_LLM bars ✓')


# ============================================================
# Figure 4: Chain amplification — contract: "Deeper chains amplify prior direction"
# ============================================================
def fig_chain():
    chain = json.load(open(f'{DATA_DIR}/chain_depth.json'))
    H_vals = [1, 2, 3, 4, 5]
    T_plot = [10, 20, 30, 50]
    colors = [P["red_strong"], P["blue_main"], P["teal"], P["violet"]]

    fig, ax = plt.subplots(figsize=(5.8, 3.0))
    # Leave SUBSTANTIAL right margin so the legend and data don't crowd
    fig.subplots_adjust(right=0.72)

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
                color=colors[idx], markersize=5, linewidth=1.3,
                markeredgewidth=0.4, markeredgecolor='white')

    ax.axhline(y=1.0, color=P["neutral_mid"], linewidth=0.7, linestyle='--')
    ax.set_xlabel('Chain Depth $H$', fontsize=10)
    ax.set_ylabel('LLM / Uniform Success Ratio', fontsize=10)
    ax.set_xticks(H_vals)
    ax.set_xlim(0.6, 5.4)
    ax.set_ylim(0.84, 1.30)
    # Legend OUTSIDE the plot area to the right
    ax.legend(loc='center left', bbox_to_anchor=(1.01, 0.5),
              frameon=True, edgecolor=P["neutral_light"],
              fontsize=8, handlelength=1.5)

    # Advantage/disadvantage shading
    ax.fill_between([0, 6], 1.0, 1.32, alpha=0.04, color=P["green_3"])
    ax.fill_between([0, 6], 0.82, 1.0, alpha=0.04, color=P["red_1"])

    fig.savefig(f'{FIG_DIR}/fig_chain_amplification.pdf', dpi=300)
    plt.close(fig)
    print('Fig 4: Chain amplification ✓')


# ============================================================
# Figure 5: Noise heatmap — contract: "Prior utility sweet spot at moderate Delta"
# ============================================================
def fig_heatmap():
    noise = json.load(open(f'{DATA_DIR}/noise_grid.json'))
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

    fig, ax = plt.subplots(figsize=(5.2, 3.0))

    im = ax.pcolormesh(pg_vals, pb_vals, advantage, cmap='RdBu_r',
                        shading='gouraud', vmin=-0.10, vmax=0.12)

    X, Y = np.meshgrid(pg_vals, pb_vals)
    cs = ax.contour(X, Y, advantage, levels=[0, 0.05],
                    colors=[P["neutral_dark"], P["teal"]],
                    linewidths=[1.2, 0.8], linestyles=['-', '--'])
    ax.clabel(cs, fmt='%.2f', fontsize=7, inline=True, inline_spacing=4)

    ax.set_xlabel(r'$p_g$ (optimal action success prob.)', fontsize=10)
    ax.set_ylabel(r'$p_b$ (suboptimal action success prob.)', fontsize=10)

    cbar = plt.colorbar(im, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label('LLM $-$ Uniform advantage', fontsize=8.5)
    cbar.ax.tick_params(labelsize=7)

    # Sweet spot annotation
    ax.annotate('Prior-utility\nsweet spot',
                xy=(0.47, 0.27), fontsize=7, ha='center',
                color=P["teal"], fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.25', fc=P["green_1"],
                          ec=P["green_3"], alpha=0.85, linewidth=0.5))

    plt.tight_layout()
    plt.savefig(f'{FIG_DIR}/fig_noise_heatmap.pdf', dpi=300)
    plt.close()
    print('Fig 5: Noise heatmap ✓')


def main():
    print('Nature-figure redraw...\n')
    fig_regret()
    fig_phase()
    fig_illm()
    fig_chain()
    fig_heatmap()
    print(f'\nSaved to {FIG_DIR}/')


if __name__ == '__main__':
    main()
