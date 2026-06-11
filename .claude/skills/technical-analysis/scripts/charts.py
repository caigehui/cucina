#!/usr/bin/env python3
"""
technical-analysis 图表脚本 —— 用 matplotlib 出深色 PNG。
子命令: trend / gex / flow。字体优先使用 Google Noto Sans SC。

通用: python charts.py <cmd> --input data.json --out out.png --symbol NVDA

输入 JSON 字段:
  trend:
    {"dates":["2026-01-02",...], "open":[...], "high":[...], "low":[...], "close":[...],
     "volume":[...]}                 # 至少 60 根, 最好 >=200 才能算 MA200
  gex:
    {"spot": 123.4,
     "chain":[{"strike":120,"call_oi":1500,"put_oi":800,"gamma":0.012}, ...]}
     # gamma 为该行权价的(可用 call/put 共用近似, 或分别给 call_gamma/put_gamma)
  flow:
    {"price_bins":[100,102,...], "volume_at_price":[...],
     "spot":123.4,
     "supports":[{"price":118,"label":"MA50"}, ...],
     "resistances":[{"price":130,"label":"Call Wall"}, ...],
     "net_flow":{"d1":1.2e7,"d5":-3e6,"d20":5e7}}   # 可选, 单位美元
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

BG = "#030807"
AX_BG = "#07110f"
PANEL = "#0b1815"
GRID = "#1f4f43"
TEXT = "#FFFFFF"
MUTED = "#FFFFFF"
GREEN = "#62f0bd"
RED = "#ff6b6b"
BLUE = "#8aa7ff"
GRAY = "#6b807a"
ORANGE = "#f5c56a"
PURPLE = "#c084fc"
BAR_BLUE = "#3db7d6"
FONT_CACHE_DIR = Path.home() / ".cache" / "cucina" / "fonts"


def _ensure_font_instance(source, cached, weight=700):
    source = Path(source)
    cached = Path(cached)
    if cached.exists():
        return cached
    if not source.exists():
        return None
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer

        FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        font = TTFont(str(source))
        instancer.instantiateVariableFont(font, {"wght": weight}, inplace=True)
        font.save(str(cached))
        return cached
    except Exception:
        return None


def _setup_style():
    noto_sans_bold = _ensure_font_instance(
        "C:/Windows/Fonts/NotoSansSC-VF.ttf",
        FONT_CACHE_DIR / "NotoSansSC-Black.ttf",
        weight=900,
    )
    noto_serif_bold = _ensure_font_instance(
        "C:/Windows/Fonts/NotoSerifSC-VF.ttf",
        FONT_CACHE_DIR / "NotoSerifSC-ExtraBold.ttf",
        weight=800,
    )
    font_candidates = [
        noto_sans_bold,
        FONT_CACHE_DIR / "NotoSansSC-Black.ttf",
        FONT_CACHE_DIR / "NotoSansSC-ExtraBold.ttf",
        FONT_CACHE_DIR / "NotoSansSC-Bold.ttf",
        "C:/Windows/Fonts/NotoSansSC-VF.ttf",
        "C:/Windows/Fonts/NotoSansCJKsc-Regular.otf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    display_candidates = [
        noto_serif_bold,
        FONT_CACHE_DIR / "NotoSerifSC-ExtraBold.ttf",
        FONT_CACHE_DIR / "NotoSerifSC-Bold.ttf",
        "C:/Windows/Fonts/NotoSerifSC-VF.ttf",
        noto_sans_bold,
        FONT_CACHE_DIR / "NotoSansSC-Black.ttf",
        "C:/Windows/Fonts/NotoSansSC-VF.ttf",
        "C:/Windows/Fonts/msyhbd.ttc",
    ]
    font_name = "Noto Sans SC"
    display_name = font_name
    for raw in font_candidates:
        if not raw:
            continue
        path = Path(raw)
        if path.exists():
            try:
                font_manager.fontManager.addfont(str(path))
                font_name = font_manager.FontProperties(fname=str(path)).get_name()
                break
            except Exception:
                continue
    for raw in display_candidates:
        if not raw:
            continue
        path = Path(raw)
        if path.exists():
            try:
                font_manager.fontManager.addfont(str(path))
                display_name = font_manager.FontProperties(fname=str(path)).get_name()
                break
            except Exception:
                continue
    plt.rcParams.update({
        "font.family": font_name,
        "font.sans-serif": [font_name, "Noto Sans SC", "Microsoft YaHei", "DejaVu Sans"],
        "font.weight": "black",
        "axes.unicode_minus": False,
        "figure.facecolor": BG,
        "axes.facecolor": AX_BG,
        "savefig.facecolor": BG,
        "savefig.edgecolor": BG,
        "text.color": TEXT,
        "axes.labelcolor": TEXT,
        "axes.titlecolor": TEXT,
        "axes.titleweight": "black",
        "axes.labelweight": "black",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": GRID,
        "grid.color": GRID,
    })
    return font_name, display_name


FONT_NAME, DISPLAY_FONT_NAME = _setup_style()


def _style_axes(*axes):
    for ax in axes:
        ax.set_facecolor(AX_BG)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.xaxis.label.set_color(TEXT)
        ax.yaxis.label.set_color(TEXT)
        ax.xaxis.label.set_fontweight("black")
        ax.yaxis.label.set_fontweight("black")
        ax.title.set_color(TEXT)
        ax.title.set_fontweight("black")
        ax.title.set_fontfamily(DISPLAY_FONT_NAME)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight("black")
            label.set_color(TEXT)
        for spine in ax.spines.values():
            spine.set_color(GRID)
            spine.set_linewidth(0.8)
        legend = ax.get_legend()
        if legend:
            frame = legend.get_frame()
            frame.set_facecolor(PANEL)
            frame.set_edgecolor(GRID)
            frame.set_alpha(0.92)
            for txt in legend.get_texts():
                txt.set_color(TEXT)
                txt.set_fontweight("black")


def _save_dark(fig, out, dpi=160):
    fig.patch.set_facecolor(BG)
    fig.tight_layout(pad=1.1)
    fig.savefig(out, dpi=dpi, facecolor=BG, edgecolor=BG, bbox_inches="tight")


def _sma(a, n):
    a = np.asarray(a, float)
    if len(a) < n:
        return np.full_like(a, np.nan)
    out = np.full_like(a, np.nan)
    c = np.cumsum(np.insert(a, 0, 0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def _adx(high, low, close, n=14):
    high, low, close = map(lambda x: np.asarray(x, float), (high, low, close))
    up = high[1:] - high[:-1]
    dn = low[:-1] - low[1:]
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum.reduce([high[1:] - low[1:],
                            np.abs(high[1:] - close[:-1]),
                            np.abs(low[1:] - close[:-1])])

    def rma(x, n):
        x = np.asarray(x, float)
        out = np.full(len(x), np.nan)
        # seed at first index with a full finite window (skip leading NaNs)
        start = None
        for i in range(len(x) - n + 1):
            w = x[i:i + n]
            if np.all(np.isfinite(w)):
                start = i + n - 1
                out[start] = np.mean(w)
                break
        if start is None:
            return out
        for i in range(start + 1, len(x)):
            xi = x[i] if np.isfinite(x[i]) else out[i - 1]
            out[i] = (out[i - 1] * (n - 1) + xi) / n
        return out

    atr = rma(tr, n)
    pdi = 100 * rma(plus_dm, n) / atr
    mdi = 100 * rma(minus_dm, n) / atr
    dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    a = np.full(len(close), np.nan)   # ADX aligned to close (dx covers bars[1:])
    a[1:] = rma(dx, n)
    return a, np.concatenate([[np.nan], pdi]), np.concatenate([[np.nan], mdi])


def _money(x, _):
    ax = abs(x)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if ax >= div:
            return f"{x/div:.1f}{suf}"
    return f"{x:.0f}"


def cmd_trend(d, out, symbol):
    close = np.asarray(d["close"], float)
    x = np.arange(len(close))
    ma20, ma50, ma200 = _sma(close, 20), _sma(close, 50), _sma(close, 200)
    adx, pdi, mdi = _adx(d["high"], d["low"], close)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), height_ratios=[3, 1], sharex=True)
    ax1.plot(x, close, color=TEXT, lw=1.5, label="Close")
    ax1.plot(x, ma20, color=BLUE, lw=1, label="MA20")
    ax1.plot(x, ma50, color=ORANGE, lw=1, label="MA50")
    ax1.plot(x, ma200, color=RED, lw=1, label="MA200")
    # regression channel
    mask = ~np.isnan(close)
    sl, ic = np.polyfit(x[mask], close[mask], 1)
    fit = sl * x + ic
    resid = close - fit
    sd = np.nanstd(resid)
    ax1.plot(x, fit, color=GRAY, ls="--", lw=0.9, label="Regression")
    ax1.fill_between(x, fit - 2 * sd, fit + 2 * sd, color=GRAY, alpha=0.16)
    trend = "UP" if sl > 0 else "DOWN"
    ax1.set_title(f"{symbol}  Trend Evidence  (slope {trend}, MA stack + channel)", fontsize=15, fontweight="black", fontfamily=DISPLAY_FONT_NAME)
    ax1.legend(loc="upper left", fontsize=9, ncol=5)
    ax1.grid(alpha=0.42)

    ax2.plot(x, adx, color=PURPLE, lw=1.2, label="ADX")
    ax2.plot(x, pdi, color=GREEN, lw=0.9, label="+DI")
    ax2.plot(x, mdi, color=RED, lw=0.9, label="-DI")
    ax2.axhline(25, color=GRAY, ls=":", lw=0.8)
    ax2.text(0, 26, "25 (trend threshold)", fontsize=8.5, color=TEXT, fontweight="black")
    ax2.set_ylim(0, max(60, np.nanmax(adx) if np.isfinite(np.nanmax(adx)) else 60))
    ax2.legend(loc="upper left", fontsize=9, ncol=3)
    ax2.grid(alpha=0.42)
    ax2.set_xlabel("bars", fontsize=11, fontweight="black")
    _style_axes(ax1, ax2)
    _save_dark(fig, out)
    print(f"saved {out}  | reg slope={sl:.4f} latest ADX={np.nanmax(adx):.1f}")


def cmd_gex(d, out, symbol):
    spot = float(d["spot"])
    chain = d["chain"]
    strikes = np.array([c["strike"] for c in chain], float)
    order = np.argsort(strikes)
    strikes = strikes[order]
    rows = [chain[i] for i in order]
    gex = []
    for c in rows:
        cg = c.get("call_gamma", c.get("gamma", 0.0))
        pg = c.get("put_gamma", c.get("gamma", 0.0))
        call = cg * c.get("call_oi", 0) * 100 * spot * spot * 0.01
        put = pg * c.get("put_oi", 0) * 100 * spot * spot * 0.01
        gex.append(call - put)            # dealer: +call, -put
    gex = np.array(gex)
    colors = [GREEN if g >= 0 else RED for g in gex]

    call_wall = strikes[int(np.argmax(gex))]
    put_wall = strikes[int(np.argmin(gex))]
    # gamma flip: cumulative gex sign change (by strike, ascending)
    cum = np.cumsum(gex)
    flip = None
    for i in range(1, len(cum)):
        if cum[i - 1] < 0 <= cum[i] or cum[i - 1] > 0 >= cum[i]:
            flip = strikes[i]
            break
    call_sum = gex[gex > 0].sum()
    put_sum = -gex[gex < 0].sum()
    pcr = put_sum / call_sum if call_sum else float("nan")

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(strikes, gex, width=(strikes[1] - strikes[0]) * 0.8 if len(strikes) > 1 else 1,
           color=colors, edgecolor="none")
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.axvline(spot, color=BLUE, ls="-", lw=1.4, label=f"Spot {spot:g}")
    ax.axvline(call_wall, color=GREEN, ls="--", lw=1.2, label=f"Call Wall {call_wall:g}")
    ax.axvline(put_wall, color=RED, ls="--", lw=1.2, label=f"Put Wall {put_wall:g}")
    if flip is not None:
        ax.axvline(flip, color=ORANGE, ls=":", lw=1.4, label=f"Gamma Flip {flip:g}")
    ax.yaxis.set_major_formatter(FuncFormatter(_money))
    ax.set_xlabel("Strike", fontsize=11, fontweight="black")
    ax.set_ylabel("Net GEX (dealer, $/1% move)", fontsize=11, fontweight="black")
    ax.set_title(f"{symbol}  Gamma Exposure   GEX PCR = {pcr:.2f}", fontsize=15, fontweight="black", fontfamily=DISPLAY_FONT_NAME)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.42, axis="y")
    _style_axes(ax)
    _save_dark(fig, out)
    print(f"saved {out}  | CallWall={call_wall:g} PutWall={put_wall:g} "
          f"Flip={flip} PCR={pcr:.2f}")


def cmd_flow(d, out, symbol):
    bins = np.asarray(d["price_bins"], float)
    vol = np.asarray(d["volume_at_price"], float)
    spot = float(d.get("spot", bins[int(np.argmax(vol))]))
    poc = bins[int(np.argmax(vol))]            # point of control (主力堆积区)

    fig, ax = plt.subplots(figsize=(10, 7))
    cols = [ORANGE if abs(b - poc) < 1e-9 else BAR_BLUE for b in bins]
    ax.barh(bins, vol, height=(bins[1] - bins[0]) * 0.85 if len(bins) > 1 else 1,
            color=cols, edgecolor="none", alpha=0.82)
    ax.axhline(spot, color=TEXT, lw=1.3, label=f"Spot {spot:g}")
    ax.axhline(poc, color=ORANGE, lw=1.3, ls="--", label=f"POC {poc:g} (main cluster)")
    for r in d.get("resistances", []):
        ax.axhline(r["price"], color=RED, lw=1, ls=":",
                   label=f"R {r['price']:g} {r.get('label','')}")
    for s in d.get("supports", []):
        ax.axhline(s["price"], color=GREEN, lw=1, ls=":",
                   label=f"S {s['price']:g} {s.get('label','')}")
    ax.xaxis.set_major_formatter(FuncFormatter(_money))
    ax.set_xlabel("Volume at price", fontsize=11, fontweight="black")
    ax.set_ylabel("Price", fontsize=11, fontweight="black")
    nf = d.get("net_flow")
    sub = ""
    if nf:
        sub = "   net flow  " + "  ".join(f"{k}:{_money(v,0)}" for k, v in nf.items())
    ax.set_title(f"{symbol}  Volume Profile + S/R{sub}", fontsize=15, fontweight="black", fontfamily=DISPLAY_FONT_NAME)
    ax.legend(loc="upper right", fontsize=8.5)
    ax.grid(alpha=0.42, axis="x")
    _style_axes(ax)
    _save_dark(fig, out)
    print(f"saved {out}  | POC={poc:g} spot={spot:g}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["trend", "gex", "flow"])
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--symbol", default="")
    a = p.parse_args()
    with open(a.input, encoding="utf-8") as f:
        d = json.load(f)
    {"trend": cmd_trend, "gex": cmd_gex, "flow": cmd_flow}[a.cmd](d, a.out, a.symbol)


if __name__ == "__main__":
    sys.exit(main())
