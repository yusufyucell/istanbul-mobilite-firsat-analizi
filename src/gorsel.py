"""Tüm grafikler için ortak stil: sade eksenler, renk körü dostu sabit palet."""
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from utils import ROOT

IMAGES = ROOT / "images"

# Kategorik renkler: sabit sırada kullanılır (renk körlüğü testinden geçmiş sıra)
MAVI, TURUNCU, CAMGOBEGI = "#2a78d6", "#eb6834", "#1baf7a"
GRI = "#b5b3ad"
YAZI, YAZI_IKINCIL = "#0b0b0b", "#52514e"
ZEMIN = "#fcfcfb"

# Büyüklük (sıralı) için tek tonlu mavi skala
MAVI_SKALA = LinearSegmentedColormap.from_list(
    "mavi", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281", "#0d366b"]
)


def stil_uygula() -> None:
    mpl.rcParams.update({
        "figure.facecolor": ZEMIN,
        "axes.facecolor": ZEMIN,
        "savefig.facecolor": ZEMIN,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "text.color": YAZI,
        "axes.labelcolor": YAZI_IKINCIL,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.edgecolor": "#d9d8d4",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,   # ızgara çizgileri verinin arkasında kalsın
        "axes.grid.axis": "y",
        "grid.color": "#ecebe8",
        "grid.linewidth": 0.8,
        "xtick.color": YAZI_IKINCIL,
        "ytick.color": YAZI_IKINCIL,
        "legend.frameon": False,
        "lines.linewidth": 2,
    })


def kaydet(fig: plt.Figure, ad: str) -> None:
    IMAGES.mkdir(exist_ok=True)
    fig.savefig(IMAGES / f"{ad}.png")


def yatay_cubuk(ax, etiketler, degerler, renk=MAVI, vurgu=None, fmt="{:.0f}"):
    """Yatay çubuk grafik: en büyük değer en üstte, değer etiketi çubuğun ucunda.

    vurgu: öne çıkarılacak etiketler (diğerleri gri çizilir)
    """
    renkler = [renk if (vurgu is None or e in vurgu) else GRI for e in etiketler]
    ax.barh(etiketler, degerler, color=renkler, height=0.7)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.tick_params(axis="y", length=0)
    for y, v in enumerate(degerler):
        ax.text(v, y, " " + fmt.format(v), va="center", fontsize=9, color=YAZI_IKINCIL)
    return ax
