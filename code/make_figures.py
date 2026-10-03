"""Generates the data figures of the paper from results/results.json.

Figures 1 to 3 are schematic rather than data bearing and are drawn in TikZ
inside paper.tex; the source is mirrored here as code/diagrams.tex.

No figure is drawn by hand and none contains a value that is not in the results
file. Figures are written as PDF into ../../figures and as PNG into
../figures_png for inspection.

Colour: the categorical slots below are the validated default palette of the
data visualisation method (blue, orange, aqua, violet, red). The three slot
subset used by the bar figures passes every check including contrast; the five
slot subset used by the sweep carries one contrast warning on the aqua step,
which is relieved by distinct markers, a legend on every panel and the same
values appearing in the tables. Hatching is retained as a second, non colour
encoding so that the figures survive greyscale printing. No figure uses a
second y-axis.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = json.load(open(os.path.join(HERE, "..", "results", "results.json")))
FIG = os.path.abspath(os.path.join(HERE, "..", "..", "figures"))
PNG = os.path.abspath(os.path.join(HERE, "..", "figures_png"))
os.makedirs(FIG, exist_ok=True)
os.makedirs(PNG, exist_ok=True)

# ---- design tokens ---------------------------------------------------------
SER = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#e34948"]
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#d5d4cf"
MUTED = "#9b9a94"
TINT = "#dce9f8"      # light blue fill for emphasised diagram boxes
SURFACE = "#ffffff"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8.5,
    "axes.labelcolor": INK,
    "axes.edgecolor": INK2,
    "axes.linewidth": 0.7,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "legend.fontsize": 7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.alpha": 1.0,
    "grid.linewidth": 0.5,
    "axes.axisbelow": True,
    "figure.dpi": 200,
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})

SYS = ["B0", "B1", "B2", "B3", "B3P", "B4", "B5"]
SYSLAB = {"B0": "B0 no retrieval", "B1": "B1 pooled", "B2": "B2 pooled+labels",
          "B3": "B3 concat", "B3P": "B3P concat+probe",
          "B4": "B4 referee", "B5": "B5 BRAIN"}


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(PNG, name + ".png"), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def bars(ax, x, values, width, label, slot, hatch=None, offset=0.0):
    return ax.bar([i + offset for i in x], values, width=width, label=label,
                  color=SER[slot], edgecolor=SURFACE, linewidth=0.9,
                  hatch=hatch)


def box(ax, x, y, w, h, text, fc=SURFACE, fs=6.5, lw=0.9, ec=INK):
    ax.add_patch(Rectangle((x, y), w, h, fill=True, facecolor=fc,
                           edgecolor=ec, linewidth=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=INK)


def arrow(ax, p, q, style="-|>", lw=0.9, ls="-", rad=0.0, color=INK):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=8,
                                 linewidth=lw, linestyle=ls, color=color,
                                 connectionstyle=f"arc3,rad={rad}",
                                 shrinkA=1, shrinkB=1))


# ---------------------------------------------------------------------------
def fig4_corpus():
    e1 = RESULTS["E1"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.2),
                             gridspec_kw=dict(wspace=0.28))
    ax = axes[0]
    cls = ["C1", "C2", "C5", "C6"]
    names = {"C1": "contradiction", "C2": "precedence", "C5": "definitional",
             "C6": "omission"}
    vals = [e1["escalation_by_class"].get(c, 0) for c in cls]
    b = ax.bar([names[c] for c in cls], vals, color=SER[0], edgecolor=SURFACE,
               linewidth=0.9, width=0.62)
    for r, v in zip(b, vals):
        ax.text(r.get_x() + r.get_width() / 2, v + 1.5, str(v), ha="center",
                fontsize=6.5, color=INK)
    ax.set_ylabel("scenarios")
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_title("organisational conflict by class")
    ax.tick_params(axis="x", rotation=12)
    ax = axes[1]
    gens = e1["distinct_version_generations_by_quarter"]
    ax.step(range(len(gens)), gens, where="post", color=SER[0], linewidth=1.4)
    ax.plot(range(len(gens)), gens, "o", markersize=3.2, color=SER[0],
            markeredgecolor=SURFACE, markeredgewidth=0.5)
    ax.set_xlabel("quarter")
    ax.set_ylabel("revision generations in force")
    ax.set_ylim(0, max(gens) + 1)
    ax.set_title("version skew across departments")
    save(fig, "fig4_corpus")


def fig5_retrieval():
    e2 = RESULTS["E2"]
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    labels = ["nDCG@10", "owner rule\nrecall", "stale share\nof served"]
    part = [e2["partitioned"]["ndcg10"], e2["partitioned"]["owner_rule_recall"],
            e2["partitioned"]["stale_share_of_served"]]
    pool = [e2["pooled"]["ndcg10"], e2["pooled"]["owner_rule_recall"],
            e2["pooled"]["stale_share_of_served"]]
    x = range(len(labels))
    bars(ax, x, part, 0.36, "partitioned", 0, offset=-0.19)
    bars(ax, x, pool, 0.36, "pooled", 1, hatch="///", offset=0.19)
    for i, (a, b) in enumerate(zip(part, pool)):
        ax.text(i - 0.19, a + 0.02, f"{a:.3f}", ha="center", fontsize=6, color=INK)
        ax.text(i + 0.19, b + 0.02, f"{b:.3f}", ha="center", fontsize=6, color=INK)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.18)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("retrieval, equal served volume")
    save(fig, "fig5_retrieval")


def fig6_detection():
    e3 = RESULTS["E3"]["by_class"]
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    cls = ["C1", "C2", "C3", "C4", "C5", "C6"]
    rec = [e3[c]["recall"] or 0 for c in cls]
    pre = [e3[c]["precision"] or 0 for c in cls]
    x = range(len(cls))
    bars(ax, x, rec, 0.36, "recall", 0, offset=-0.19)
    bars(ax, x, pre, 0.36, "precision", 1, hatch="///", offset=0.19)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{c}\nn={e3[c]['support']}" for c in cls])
    ax.set_ylim(0, 1.34)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.legend(frameon=False, ncol=2, loc="upper center")
    ax.set_title("conflict detection by class")
    save(fig, "fig6_detection")


def fig7_systems():
    e4 = RESULTS["E4"]["systems"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.4),
                             gridspec_kw=dict(wspace=0.22))
    x = range(len(SYS))
    ax = axes[0]
    cov = [e4[s]["coverage"] for s in SYS]
    spu = [e4[s]["spurious_rate"] for s in SYS]
    bars(ax, x, cov, 0.36, "obligation coverage", 0, offset=-0.19)
    bars(ax, x, spu, 0.36, "spurious obligation rate", 1, hatch="///", offset=0.19)
    ax.set_xticks(list(x)); ax.set_xticklabels(SYS)
    ax.set_ylim(0, 1.42); ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("what is asserted")
    ax = axes[1]
    attr = [e4[s]["attribution_rate"] or 0 for s in SYS]
    jur = [e4[s]["jurisdiction_violation_rate"] or 0 for s in SYS]
    una = [e4[s]["unattributed_rate"] or 0 for s in SYS]
    bars(ax, x, attr, 0.26, "correct attribution", 0, offset=-0.26)
    bars(ax, x, jur, 0.26, "jurisdiction violation", 1, hatch="///")
    bars(ax, x, una, 0.26, "unattributed", 3, hatch="...", offset=0.26)
    ax.set_xticks(list(x)); ax.set_xticklabels(SYS)
    ax.set_ylim(0, 1.62); ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("who is accountable")
    save(fig, "fig7_systems")


def fig8_silent():
    e4 = RESULTS["E4"]["systems"]
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    vals = [e4[s]["silent_wrong_answer_rate"] or 0 for s in SYS]
    # colour here is emphasis, not identity; the proposed framework is
    # red in every figure where it is singled out
    colours = [SER[0]] * (len(SYS) - 1) + [SER[4]]
    b = ax.bar(SYS, vals, color=colours, edgecolor=SURFACE, linewidth=0.9,
               width=0.66)
    for r, v in zip(b, vals):
        ax.text(r.get_x() + r.get_width() / 2, v + 0.025, f"{v:.3f}",
                ha="center", fontsize=6.5, color=INK)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("rate on scenarios needing escalation")
    ax.set_title("silent wrong answers")
    save(fig, "fig8_silent")


def fig9_sweep():
    sw = RESULTS["SWEEP"]
    lams = RESULTS["lambda_grid"]
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.3),
                             gridspec_kw=dict(wspace=0.3))
    order = ["B1", "B3", "B3P", "B4", "B5"]
    marks = {"B1": "s", "B3": "^", "B3P": "D", "B4": "v", "B5": "o"}
    for ax, key, title in [
            (axes[0], "silent_wrong_answer_rate", "silent wrong answers"),
            (axes[1], "spurious_rate", "spurious obligation rate"),
            (axes[2], "coverage", "obligation coverage")]:
        for i, s in enumerate(order):
            ys = [sw[str(l)][s][key] or 0 for l in lams]
            ax.plot(lams, ys, marker=marks[s], markersize=3.4, linewidth=1.5,
                    color=SER[i], markeredgecolor=SURFACE, markeredgewidth=0.5,
                    label=SYSLAB[s])
        ax.set_xlabel(r"agent failure rate $\lambda$")
        ax.set_title(title)
        ax.set_ylim(0, 1.02)
        ax.axvline(RESULTS["lambda_star"], color=MUTED, linewidth=0.8,
                   linestyle=":")
    axes[0].set_ylabel("rate")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, ncol=5, loc="lower center",
               bbox_to_anchor=(0.5, -0.13))
    save(fig, "fig9_sweep")


def fig10_adversarial():
    e6 = RESULTS["E6"]
    keys = [("baseline", "no attack"), ("captured_SEC", "captured SEC"),
            ("captured_LEG", "captured LEG"), ("poisoned_B5", "poisoned partition"),
            ("fabrication", "citation fabrication"),
            ("stale_exploitation", "stale exploitation"),
            ("hostile_lattice_SEC", "hostile lattice")]
    fig, ax = plt.subplots(figsize=(7.0, 2.5))
    labs = [l for _, l in keys]
    jur = [e6[k]["jurisdiction_violation_rate"] or 0 for k, _ in keys]
    sil = [e6[k]["silent_wrong_answer_rate"] or 0 for k, _ in keys]
    spu = [e6[k]["spurious_rate"] or 0 for k, _ in keys]
    x = range(len(keys))
    bars(ax, x, jur, 0.26, "jurisdiction violation", 0, offset=-0.26)
    bars(ax, x, sil, 0.26, "silent wrong answer", 1, hatch="///")
    bars(ax, x, spu, 0.26, "spurious obligation", 3, hatch="...", offset=0.26)
    ax.set_xticks(list(x)); ax.set_xticklabels(labs, rotation=12, ha="right")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.set_ylim(0, max(jur + sil + spu) * 1.55)
    ax.set_title("the proposed framework under adversarial conditions")
    save(fig, "fig10_adversarial")


def fig11_ablation():
    e8 = RESULTS["E8"]
    keys = ["full", "no_R0_admissibility", "no_R1_currency", "no_R2_jurisdiction",
            "no_R3_precedence", "no_R4_evidence", "no_R5_completeness",
            "no_completeness_probe", "no_R6_ordering", "no_R7_definitional",
            "no_escalation"]
    labs = ["full", "-R0", "-R1", "-R2", "-R3", "-R4", "-R5", "-probe", "-R6",
            "-R7", "-escalate"]
    fig, ax = plt.subplots(figsize=(7.0, 2.4))
    cov = [e8[k]["coverage"] or 0 for k in keys]
    spu = [e8[k]["spurious_rate"] or 0 for k in keys]
    sil = [e8[k]["silent_wrong_answer_rate"] or 0 for k in keys]
    x = range(len(keys))
    bars(ax, x, cov, 0.26, "coverage", 0, offset=-0.26)
    bars(ax, x, spu, 0.26, "spurious rate", 1, hatch="///")
    bars(ax, x, sil, 0.26, "silent wrong answer", 3, hatch="...", offset=0.26)
    ax.set_xticks(list(x)); ax.set_xticklabels(labs)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.set_ylim(0, 1.35); ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_title("ablation of the reconciliation rules")
    save(fig, "fig11_ablation")


def fig12_cost():
    e7 = RESULTS["E7"]
    sc = e7["scaling_in_departments"]
    ks = sorted(sc, key=int)
    xs = [int(k) for k in ks]
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.2),
                             gridspec_kw=dict(wspace=0.34))
    ax = axes[0]
    ax.plot(xs, [sc[k]["served"] for k in ks], marker="o", markersize=3.4,
            color=SER[0], linewidth=1.5, markeredgecolor=SURFACE,
            markeredgewidth=0.5)
    ax.set_xlabel("departments"); ax.set_ylabel("artefacts served")
    ax.set_xticks(xs); ax.set_title("context cost")
    ax = axes[1]
    ax.plot(xs, [sc[k]["seconds_per_scenario"] * 1000 for k in ks], marker="s",
            markersize=3.4, color=SER[1], linewidth=1.5,
            markeredgecolor=SURFACE, markeredgewidth=0.5)
    ax.set_xlabel("departments"); ax.set_ylabel("reconciliation, ms")
    ax.set_xticks(xs); ax.set_title("reconciliation time")
    ax = axes[2]
    vals = [RESULTS["E4"]["systems"][s]["mean_served_artefacts"] for s in SYS]
    b = ax.bar(SYS, vals, color=SER[0], edgecolor=SURFACE, linewidth=0.9,
               width=0.66)
    for r, v in zip(b, vals):
        ax.text(r.get_x() + r.get_width() / 2, v + 3, f"{v:.0f}", ha="center",
                fontsize=6, color=INK)
    ax.set_ylabel("artefacts served")
    ax.set_ylim(0, max(vals) * 1.22)
    ax.tick_params(axis="x", labelsize=6)
    ax.set_title("served volume by system")
    save(fig, "fig12_cost")


if __name__ == "__main__":
    fig4_corpus(); fig5_retrieval(); fig6_detection(); fig7_systems()
    fig8_silent(); fig9_sweep(); fig10_adversarial(); fig11_ablation()
    fig12_cost()
    print("all figures written to", FIG)
