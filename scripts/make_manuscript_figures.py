from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "writings" / "original" / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def pipeline() -> None:
    fig, ax = plt.subplots(figsize=(10, 2.25))
    ax.axis("off")
    boxes = [
        ("Input image", 0.03, "#e8f1f8"),
        ("Preprocess\nmetadata", 0.20, "#e8f1f8"),
        ("Candidate maps\nSIFT | JPEG | resampling | block", 0.40, "#f6efe3"),
        ("Validation-only\nnormalization + fusion", 0.68, "#e9f3e6"),
        ("Mask + metrics\nheld-out only", 0.87, "#f3e6e9"),
    ]
    for label, x, color in boxes:
        ax.text(x, 0.5, label, ha="center", va="center", fontsize=9,
                bbox={"boxstyle": "round,pad=0.55", "facecolor": color,
                      "edgecolor": "#31424f", "linewidth": 1.0},
                transform=ax.transAxes)
    for left, right in zip([0.11, 0.31, 0.56, 0.78], [0.17, 0.37, 0.63, 0.82]):
        ax.annotate("", xy=(right, 0.5), xytext=(left, 0.5),
                    xycoords=ax.transAxes, textcoords=ax.transAxes,
                    arrowprops={"arrowstyle": "->", "lw": 1.2, "color": "#31424f"})
    fig.tight_layout(pad=0.4)
    fig.savefig(FIG / "pipeline.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def bars() -> None:
    labels = ["J+R+B", "C+J+R+B", "C+R+B", "R+B", "B"]
    values = [0.1875, 0.1875, 0.1822, 0.1787, 0.1761]
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    colors = ["#4c78a8", "#b5bdc7", "#9ecae1", "#c6dbef", "#e5e5e5"]
    bars_ = ax.bar(labels, values, color=colors, edgecolor="#31424f", linewidth=0.6)
    ax.set_ylabel("Validation Dice")
    ax.set_xlabel("Cue subset (C copy-move, J JPEG, R resampling, B block-grid)")
    ax.set_ylim(0, 0.22)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6)
    ax.set_axisbelow(True)
    for bar, value in zip(bars_, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.004,
                f"{value:.4f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "pilot_ablation.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    kinds = ["Copy-move", "Splicing", "Object\nreplacement", "Geometric\nedit"]
    values = [0.1355, 0.2890, 0.1218, 0.2785]
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    ax.bar(kinds, values, color="#7aa6c2", edgecolor="#31424f", linewidth=0.6)
    ax.set_ylabel("Held-out pilot Dice")
    ax.set_ylim(0, 0.34)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6)
    ax.set_axisbelow(True)
    for index, value in enumerate(values):
        ax.text(index, value + 0.006, f"{value:.4f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "pilot_by_manipulation.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def public_example() -> None:
    image_dir = ROOT / "references" / "datasets" / "comofod_examples"
    original = np.asarray(Image.open(image_dir / "006_O.png").convert("RGB"))
    forged = np.asarray(Image.open(image_dir / "006_F.png").convert("RGB"))
    score = np.mean(np.abs(forged.astype(float) - original.astype(float)), axis=2)
    fig, axes = plt.subplots(1, 3, figsize=(8.2, 2.8))
    axes[0].imshow(original)
    axes[0].set_title("CoMoFoD original")
    axes[1].imshow(forged)
    axes[1].set_title("CoMoFoD forged")
    axes[2].imshow(forged)
    axes[2].imshow(score, cmap="magma", alpha=0.58, vmin=0, vmax=1)
    axes[2].set_title("Difference view\n(not a ground-truth mask)")
    for axis in axes:
        axis.axis("off")
    fig.tight_layout(w_pad=0.4)
    fig.savefig(FIG / "comofod_example.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    pipeline()
    bars()
    public_example()
