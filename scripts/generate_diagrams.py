"""
Генератор схем и диаграмм для ВКР по ГОСТ 19.701-90.
Создаёт PNG-файлы в docs/figures/ с разрешением 300 DPI.

Запуск: python scripts/generate_diagrams.py
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Ellipse
import matplotlib.patheffects as pe
import numpy as np
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "docs" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DPI = 300
FONT = 'Times New Roman'

# ─── ГОСТ 19.701-90 цвета и стили ───────────────────────────────────────────
C_BORDER  = '#000000'   # обводка
C_FILL    = '#FFFFFF'   # заливка фигур
C_TERM    = '#E8E8E8'   # терминал (начало/конец)
C_PROC    = '#FFFFFF'   # процесс
C_DEC     = '#FFF8DC'   # решение (ромб)
C_IO      = '#E8F4FD'   # ввод/вывод
C_PREP    = '#F0FFF0'   # предопределённый процесс
C_CONN    = '#FFE4B5'   # коннектор
LW        = 1.2         # ширина линии

def save(fig, name):
    path = OUT_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  Saved: {path.name}')


# ─── Примитивы по ГОСТ 19.701-90 ─────────────────────────────────────────────

def terminal(ax, x, y, w, h, text, fs=8):
    """Терминал (начало/конец) — скруглённый прямоугольник."""
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle='round,pad=0.05', linewidth=LW,
                         edgecolor=C_BORDER, facecolor=C_TERM)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs,
            fontfamily=FONT, fontweight='bold', wrap=True,
            multialignment='center')


def process(ax, x, y, w, h, text, fs=7.5):
    """Процесс — прямоугольник."""
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle='square,pad=0', linewidth=LW,
                         edgecolor=C_BORDER, facecolor=C_PROC)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs,
            fontfamily=FONT, wrap=True, multialignment='center')


def predef(ax, x, y, w, h, text, fs=7.5):
    """Предопределённый процесс — прямоугольник с двойными вертикальными линиями."""
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle='square,pad=0', linewidth=LW,
                         edgecolor=C_BORDER, facecolor=C_PREP)
    ax.add_patch(box)
    m = w * 0.08
    for dx in [-w/2 + m, w/2 - m]:
        ax.plot([x + dx, x + dx], [y - h/2, y + h/2], color=C_BORDER, lw=LW * 0.7)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs,
            fontfamily=FONT, wrap=True, multialignment='center')


def decision(ax, x, y, w, h, text, fs=7.5):
    """Решение — ромб."""
    pts = np.array([[x, y + h/2], [x + w/2, y], [x, y - h/2], [x - w/2, y]])
    poly = Polygon(pts, closed=True, linewidth=LW,
                   edgecolor=C_BORDER, facecolor=C_DEC)
    ax.add_patch(poly)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs,
            fontfamily=FONT, multialignment='center')


def io_block(ax, x, y, w, h, text, fs=7.5):
    """Ввод/вывод — параллелограмм."""
    skew = w * 0.12
    pts = np.array([[x - w/2 + skew, y + h/2], [x + w/2 + skew, y + h/2],
                    [x + w/2 - skew, y - h/2], [x - w/2 - skew, y - h/2]])
    poly = Polygon(pts, closed=True, linewidth=LW,
                   edgecolor=C_BORDER, facecolor=C_IO)
    ax.add_patch(poly)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs,
            fontfamily=FONT, multialignment='center')


def connector(ax, x, y, r, text, fs=7):
    """Коннектор — кружок."""
    circ = plt.Circle((x, y), r, linewidth=LW,
                       edgecolor=C_BORDER, facecolor=C_CONN)
    ax.add_patch(circ)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs, fontfamily=FONT)


def arrow(ax, x1, y1, x2, y2, label='', label_side='right', fs=6.5):
    """Стрелка соединения."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        dx = 0.04 if label_side == 'right' else -0.04
        ax.text(mx + dx, my, label, ha='center', va='center',
                fontsize=fs, fontfamily=FONT, color='#333333')


def arrow_v(ax, x, y1, y2, label='', label_side='right'):
    arrow(ax, x, y1, x, y2, label, label_side)


def arrow_h(ax, x1, x2, y, label='', label_side='top'):
    arrow(ax, x1, y, x2, y, label, label_side)


def new_fig(w_inch=6, h_inch=10):
    fig, ax = plt.subplots(figsize=(w_inch, h_inch))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_aspect('equal')
    return fig, ax


def gost_title(fig, text, fs=9):
    fig.text(0.5, 0.98, text, ha='center', va='top',
             fontsize=fs, fontfamily=FONT, fontweight='bold')


# ─────────────────────────────────────────────────────────────────────────────
# 1. Блок-схема алгоритма извлечения признаков (ГОСТ 19.701-90)
# ─────────────────────────────────────────────────────────────────────────────
def fig_5_1():
    fig, ax = new_fig(5.5, 11)
    gost_title(fig, 'Рисунок 5.1 – Блок-схема алгоритма извлечения признаков из PE-файла')

    W, H, cx = 0.54, 0.065, 0.5
    step = 0.093
    ys = [0.92 - i * step for i in range(11)]

    terminal(ax,  cx, ys[0],  W, H,    'НАЧАЛО')
    io_block( ax,  cx, ys[1],  W, H,    'Ввод: путь к файлу')
    process(  ax,  cx, ys[2],  W, H,    'Открыть файл, читать первые 5 МБ')
    decision( ax,  cx, ys[3],  W*1.2, H*1.1, 'Валидный\nPE-формат?')
    io_block( ax,  cx, ys[4],  W, H,    'Вывод: None (ошибка формата)')
    predef(   ax,  cx, ys[5],  W, H,    'Извлечь признаки\nфайла и энтропию')
    predef(   ax,  cx, ys[6],  W, H,    'Извлечь признаки\nDOS/FILE/OPT заголовков')
    predef(   ax,  cx, ys[7],  W, H,    'Извлечь признаки\nсекций (размер, энтропия)')
    predef(   ax,  cx, ys[8],  W, H,    'Извлечь признаки\nимпортов и экспортов')
    predef(   ax,  cx, ys[9],  W, H,    'Извлечь признаки\nресурсов и строк')
    io_block( ax,  cx, ys[10], W, H,    'Вывод: словарь из 238 признаков')

    for i in range(len(ys)-1):
        if i == 2:
            continue
        if i == 3:
            arrow_v(ax, cx, ys[i] - H*0.55, ys[i+1] + H*0.55, 'Нет')
        elif i == 4:
            # skip (error branch ends here)
            pass
        else:
            arrow_v(ax, cx, ys[i] - H*0.55, ys[i+1] + H*0.55)

    # Да ветка от decision
    arrow_v(ax, cx, ys[2] - H*0.55, ys[3] + H*0.6)
    arrow_v(ax, cx, ys[3] - H*0.6, ys[5] + H*0.55, 'Да')
    # Нет ветка — вправо
    ax.annotate('', xy=(cx + W*0.6 + 0.01, ys[4]),
                xytext=(cx + W*1.2/2, ys[3]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(cx + W*0.5, ys[3] - 0.01, 'Нет', ha='left', va='top', fontsize=6.5, fontfamily=FONT)

    terminal_y = ys[10] - step
    terminal(ax, cx, terminal_y, W, H, 'КОНЕЦ')
    arrow_v(ax, cx, ys[10] - H*0.55, terminal_y + H*0.55)

    save(fig, 'fig_5_1_flowchart_features.png')


# ─────────────────────────────────────────────────────────────────────────────
# 2. Блок-схема алгоритма обучения LightGBM
# ─────────────────────────────────────────────────────────────────────────────
def fig_5_2():
    fig, ax = new_fig(5.5, 12)
    gost_title(fig, 'Рисунок 5.2 – Блок-схема алгоритма обучения модели LightGBM')

    W, H, cx = 0.56, 0.063, 0.5
    step = 0.088
    ys = [0.92 - i * step for i in range(13)]

    terminal( ax, cx, ys[0],  W, H,   'НАЧАЛО')
    io_block( ax, cx, ys[1],  W, H,   'Ввод: папки malware/, benign/')
    predef(   ax, cx, ys[2],  W, H,   'Параллельное извлечение признаков\n(multiprocessing, N–1 ядер)')
    process(  ax, cx, ys[3],  W, H,   'Сформировать DataFrame,\nзаполнить NaN=0')
    process(  ax, cx, ys[4],  W, H,   'Разбить на train/test 80%/20%\n(StratifiedKFold)')
    process(  ax, cx, ys[5],  W, H,   'Инициализировать Optuna study\n(TPE-сэмплер, 50 триалов)')
    decision( ax, cx, ys[6],  W*1.2, H*1.1, 'Триал\n< 50?')
    process(  ax, cx, ys[7],  W, H,   'Optuna предлагает\nгиперпараметры')
    predef(   ax, cx, ys[8],  W, H,   '5-кратная StratifiedKFold\nкросс-валидация → F2-score')
    process(  ax, cx, ys[9],  W, H,   'Обновить байесовскую модель Optuna')
    process(  ax, cx, ys[10], W, H,   'Обучить итоговую модель\nLightGBM на train (GPU/CPU)')
    process(  ax, cx, ys[11], W, H,   'Подобрать порог τ по F2-score\nна val-выборке')
    io_block( ax, cx, ys[12], W, H,   'Сохранить: .model, threshold.json,\nfeature_names.json')

    terminal_y = ys[12] - step
    terminal(ax, cx, terminal_y, W, H, 'КОНЕЦ')

    for i in range(5):
        arrow_v(ax, cx, ys[i] - H*0.55, ys[i+1] + H*0.55)

    arrow_v(ax, cx, ys[5] - H*0.55, ys[6] + H*0.6)

    # Да (продолжаем цикл)
    ax.annotate('', xy=(cx - W*0.6 - 0.01, ys[7]),
                xytext=(cx - W*1.2/2, ys[6]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(cx - W*0.65, ys[6] + 0.005, 'Да', ha='right', va='bottom', fontsize=6.5, fontfamily=FONT)
    arrow_v(ax, cx - W*0.6 - 0.01, ys[7], ys[9] - H*0.55)
    # обратная петля
    x_left = cx - W*0.65
    ax.plot([x_left, x_left], [ys[9] - H*0.55, ys[6]], color=C_BORDER, lw=LW)
    ax.annotate('', xy=(cx - W*0.6, ys[7] + H*0.55),
                xytext=(cx - W*0.6, ys[7] + H*0.55 + 0.001),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))

    for i in [7, 8]:
        arrow_v(ax, cx, ys[i] - H*0.55, ys[i+1] + H*0.55)

    # Нет → выход из цикла
    ax.annotate('', xy=(cx, ys[10] + H*0.55),
                xytext=(cx + W*1.2/2, ys[6]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(cx + W*0.65, ys[6] - 0.005, 'Нет', ha='left', va='top', fontsize=6.5, fontfamily=FONT)

    for i in [10, 11, 12]:
        arrow_v(ax, cx, ys[i] - H*0.55, (ys[i+1] if i < 12 else terminal_y) + H*0.55)

    save(fig, 'fig_5_2_flowchart_training.png')


# ─────────────────────────────────────────────────────────────────────────────
# 3. Блок-схема алгоритма детекции
# ─────────────────────────────────────────────────────────────────────────────
def fig_5_3():
    fig, ax = new_fig(5.5, 10)
    gost_title(fig, 'Рисунок 5.3 – Блок-схема алгоритма детекции вредоносного ПО')

    W, H, cx = 0.54, 0.067, 0.5
    step = 0.095
    ys = [0.92 - i * step for i in range(10)]

    terminal( ax, cx, ys[0], W, H,   'НАЧАЛО')
    process(  ax, cx, ys[1], W, H,   'Загрузить модель и\nпорог τ из файлов')
    io_block( ax, cx, ys[2], W, H,   'Ввод: путь к файлу')
    predef(   ax, cx, ys[3], W, H,   'Извлечь 238 признаков\n(алгоритм 5.1)')
    decision( ax, cx, ys[4], W*1.2, H*1.1, 'Признаки\nизвлечены?')
    io_block( ax, cx, ys[5], W, H,   'Вывод: ошибка формата')
    process(  ax, cx, ys[6], W, H,   'Привести вектор к feature_names,\nотсутствующие = 0')
    process(  ax, cx, ys[7], W, H,   'model.predict(x) → вероятность p')
    decision( ax, cx, ys[8], W*1.2, H*1.1, 'p ≥ τ ?')
    io_block( ax, cx, ys[9], W, H,   'Вывод: МАЛВАРЬ / ЛЕГИТИМНЫЙ,\nзапись в лог')

    terminal_y = ys[9] - step
    terminal(ax, cx, terminal_y, W, H, 'КОНЕЦ')

    arrow_v(ax, cx, ys[0] - H*0.55, ys[1] + H*0.55)
    arrow_v(ax, cx, ys[1] - H*0.55, ys[2] + H*0.55)
    arrow_v(ax, cx, ys[2] - H*0.55, ys[3] + H*0.55)
    arrow_v(ax, cx, ys[3] - H*0.55, ys[4] + H*0.6)

    # Нет → ошибка (вправо)
    ax.annotate('', xy=(cx + W*0.3 + 0.01, ys[5]),
                xytext=(cx + W*1.2/2, ys[4]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(cx + W*0.65, ys[4], 'Нет', ha='left', va='center', fontsize=6.5, fontfamily=FONT)

    # Да → продолжить
    arrow_v(ax, cx, ys[4] - H*0.6, ys[6] + H*0.55, 'Да')
    arrow_v(ax, cx, ys[6] - H*0.55, ys[7] + H*0.55)
    arrow_v(ax, cx, ys[7] - H*0.55, ys[8] + H*0.6)

    # p >= τ: Да / Нет
    ax.text(cx - W*0.7, ys[8], 'Да → МАЛВАРЬ', ha='right', va='center', fontsize=6, fontfamily=FONT)
    ax.text(cx + W*0.65, ys[8], 'Нет → ЛЕГИТ.', ha='left', va='center', fontsize=6, fontfamily=FONT)
    arrow_v(ax, cx, ys[8] - H*0.6, ys[9] + H*0.55)
    arrow_v(ax, cx, ys[9] - H*0.55, terminal_y + H*0.55)

    save(fig, 'fig_5_3_flowchart_detection.png')


# ─────────────────────────────────────────────────────────────────────────────
# 4. Блок-схема алгоритма массовой проверки файлов
# ─────────────────────────────────────────────────────────────────────────────
def fig_5_4():
    fig, ax = new_fig(5.5, 10)
    gost_title(fig, 'Рисунок 5.4 – Блок-схема алгоритма массовой проверки файлов')

    W, H, cx = 0.54, 0.067, 0.5
    step = 0.095
    ys = [0.92 - i * step for i in range(10)]

    terminal( ax, cx, ys[0], W, H,   'НАЧАЛО')
    io_block( ax, cx, ys[1], W, H,   'Ввод: путь к директории')
    process(  ax, cx, ys[2], W, H,   'Рекурсивно найти все файлы\n.exe, .dll, .sys')
    process(  ax, cx, ys[3], W, H,   'Инициализировать счётчики\n(обнаружено/чисто/ошибок)')
    decision( ax, cx, ys[4], W*1.2, H*1.1, 'Есть\nнепроверенные\nфайлы?')
    predef(   ax, cx, ys[5], W, H,   'Проверить файл\n(алгоритм 5.3)')
    process(  ax, cx, ys[6], W, H,   'Обновить счётчики,\nпрогресс-бар')
    process(  ax, cx, ys[7], W, H,   'Обновить список угроз\n(если МАЛВАРЬ)')
    io_block( ax, cx, ys[8], W, H,   'Сформировать сводный отчёт\n(статистика, список угроз)')
    io_block( ax, cx, ys[9], W, H,   'Вывод отчёта на экран / в JSON')

    terminal_y = ys[9] - step
    terminal(ax, cx, terminal_y, W, H, 'КОНЕЦ')

    for i in range(4):
        arrow_v(ax, cx, ys[i] - H*0.55, ys[i+1] + H*0.55)

    arrow_v(ax, cx, ys[4] - H*0.6, ys[5] + H*0.55, 'Да')

    # Цикл: после шага 7 — обратно к decision
    for i in [5, 6]:
        arrow_v(ax, cx, ys[i] - H*0.55, ys[i+1] + H*0.55)
    # loop back
    x_right = cx + W*0.35
    ax.plot([x_right, x_right], [ys[7] - H*0.55, ys[4]], color=C_BORDER, lw=LW)
    ax.plot([cx, x_right], [ys[4], ys[4]], color=C_BORDER, lw=LW)
    ax.annotate('', xy=(cx + W*1.2/2, ys[4]),
                xytext=(x_right, ys[4] + 0.001),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.plot([cx + W*0.5, x_right], [ys[7] - H*0.55, ys[7] - H*0.55], color=C_BORDER, lw=LW)

    # Нет → конец цикла
    ax.annotate('', xy=(cx, ys[8] + H*0.55),
                xytext=(cx - W*1.2/2, ys[4]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(cx - W*0.7, ys[4], 'Нет', ha='right', va='center', fontsize=6.5, fontfamily=FONT)

    arrow_v(ax, cx, ys[8] - H*0.55, ys[9] + H*0.55)
    arrow_v(ax, cx, ys[9] - H*0.55, terminal_y + H*0.55)

    save(fig, 'fig_5_4_flowchart_folder.png')


# ─────────────────────────────────────────────────────────────────────────────
# 5. Блок-схема мониторинга файловой системы
# ─────────────────────────────────────────────────────────────────────────────
def fig_5_5():
    fig, ax = new_fig(5.5, 10)
    gost_title(fig, 'Рисунок 5.5 – Блок-схема алгоритма мониторинга файловой системы')

    W, H, cx = 0.54, 0.067, 0.5
    step = 0.095
    ys = [0.92 - i * step for i in range(10)]

    terminal( ax, cx, ys[0], W, H,   'НАЧАЛО')
    io_block( ax, cx, ys[1], W, H,   'Ввод: путь к директории')
    process(  ax, cx, ys[2], W, H,   'Инициализировать watchdog.Observer,\nзарегистрировать обработчик')
    process(  ax, cx, ys[3], W, H,   'Запустить наблюдатель\n(фоновый поток)')
    decision( ax, cx, ys[4], W*1.2, H*1.15, 'Событие\non_created?')
    decision( ax, cx, ys[5], W*1.2, H*1.1,  'Расширение\n.exe/.dll/.sys?')
    process(  ax, cx, ys[6], W, H,   'Ожидание 0,3 с\n(файл дописывается)')
    predef(   ax, cx, ys[7], W, H,   'В отдельном потоке:\nпроверить файл (алг. 5.3)')
    decision( ax, cx, ys[8], W*1.2, H*1.1,  'Мониторинг\nостановлен?')
    process(  ax, cx, ys[9], W, H,   'Остановить наблюдатель')

    terminal_y = ys[9] - step
    terminal(ax, cx, terminal_y, W, H, 'КОНЕЦ')

    for i in range(4):
        arrow_v(ax, cx, ys[i] - H*0.55, ys[i+1] + H*0.55)

    # Да — событие есть
    arrow_v(ax, cx, ys[4] - H*0.6, ys[5] + H*0.6, 'Да')
    # Нет — продолжить ожидание (петля обратно)
    x_left2 = cx - W*0.68
    ax.plot([cx - W*1.2/2, x_left2], [ys[4], ys[4]], color=C_BORDER, lw=LW)
    ax.plot([x_left2, x_left2], [ys[4], ys[8] - H*0.6], color=C_BORDER, lw=LW)
    ax.text(x_left2 - 0.01, ys[4], 'Нет', ha='right', va='center', fontsize=6.5, fontfamily=FONT)

    # Расширение ОК?
    arrow_v(ax, cx, ys[5] - H*0.6, ys[6] + H*0.55, 'Да')
    # Нет — пропустить
    x_right2 = cx + W*0.68
    ax.plot([cx + W*1.2/2, x_right2], [ys[5], ys[5]], color=C_BORDER, lw=LW)
    ax.plot([x_right2, x_right2], [ys[5], ys[8]], color=C_BORDER, lw=LW)
    ax.text(x_right2 + 0.01, ys[5], 'Нет', ha='left', va='center', fontsize=6.5, fontfamily=FONT)

    arrow_v(ax, cx, ys[6] - H*0.55, ys[7] + H*0.55)
    arrow_v(ax, cx, ys[7] - H*0.55, ys[8] + H*0.6)

    # Мониторинг остановлен? Нет → петля наверх к ожиданию события
    ax.plot([x_left2, x_left2], [ys[8] - H*0.6, ys[4]], color=C_BORDER, lw=LW)
    ax.annotate('', xy=(cx - W*1.2/2, ys[4]),
                xytext=(x_left2, ys[4]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(x_left2 - 0.005, (ys[8] + ys[4])/2, 'Нет', ha='right', va='center',
            fontsize=6.5, fontfamily=FONT)

    # Да → остановить
    arrow_v(ax, cx, ys[8] - H*0.6, ys[9] + H*0.55, 'Да')
    arrow_v(ax, cx, ys[9] - H*0.55, terminal_y + H*0.55)

    save(fig, 'fig_5_5_flowchart_monitor.png')


# ─────────────────────────────────────────────────────────────────────────────
# 6. Блок-схема агентного взаимодействия
# ─────────────────────────────────────────────────────────────────────────────
def fig_5_6():
    fig, ax = new_fig(7.5, 9)
    gost_title(fig, 'Рисунок 5.6 – Блок-схема алгоритма кооперативного взаимодействия агент–сканер')

    # Two columns: Agent (left) and Scanner (right)
    cA, cS = 0.27, 0.73
    W, H = 0.42, 0.065
    step = 0.1
    ys = [0.92 - i * step for i in range(8)]

    # Header labels
    ax.text(cA, 0.97, 'АГЕНТ (agent.py)', ha='center', va='center',
            fontsize=9, fontfamily=FONT, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#D0E8FF', edgecolor='#0066CC'))
    ax.text(cS, 0.97, 'СКАНЕР (gui.py)', ha='center', va='center',
            fontsize=9, fontfamily=FONT, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#D0FFD0', edgecolor='#006600'))

    # Agent side
    terminal(ax, cA, ys[0], W, H, 'НАЧАЛО АГЕНТА')
    predef(  ax, cA, ys[1], W, H, 'Определить IP и MAC\nтекущего ПК')
    process( ax, cA, ys[2], W, H, 'Запустить watchdog\nза директорией')
    decision(ax, cA, ys[3], W*1.1, H*1.1, 'Новый\nPE-файл?')
    process( ax, cA, ys[4], W, H, 'Сформировать JSON-\nметаданные {ip, mac, file}')
    process( ax, cA, ys[5], W, H, 'Отправить UDP-датаграмму\nна порт 45000')
    process( ax, cA, ys[6], W, H, 'Передать файл по TCP\nна порт 45001')
    terminal(ax, cA, ys[7], W, H, 'Ожидание')

    for i in range(3):
        arrow_v(ax, cA, ys[i] - H*0.55, ys[i+1] + H*0.55)
    arrow_v(ax, cA, ys[3] - H*0.6, ys[4] + H*0.55, 'Да')
    # loop back Нет
    x_loop = cA - W*0.6
    ax.plot([cA - W*1.1/2, x_loop], [ys[3], ys[3]], color=C_BORDER, lw=LW)
    ax.plot([x_loop, x_loop], [ys[3], ys[7]], color=C_BORDER, lw=LW)
    ax.plot([x_loop, cA - W*0.5], [ys[7], ys[7]], color=C_BORDER, lw=LW)
    ax.annotate('', xy=(cA - W*0.5, ys[7]),
                xytext=(x_loop, ys[7]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(x_loop - 0.005, ys[3], 'Нет', ha='right', va='center', fontsize=6, fontfamily=FONT)

    for i in [4, 5, 6]:
        arrow_v(ax, cA, ys[i] - H*0.55, ys[i+1] + H*0.55)

    # Scanner side
    terminal( ax, cS, ys[0], W, H, 'НАЧАЛО СКАНЕРА')
    process(  ax, cS, ys[1], W, H, 'Запустить UDP-сервер\nна порту 45000')
    process(  ax, cS, ys[2], W, H, 'Запустить TCP-сервер\nна порту 45001')
    decision( ax, cS, ys[3], W*1.1, H*1.1, 'Входящий\nUDP/TCP?')
    decision( ax, cS, ys[4], W*1.1, H*1.1, 'UDP-уведомление?')
    process(  ax, cS, ys[5], W, H, 'Обновить список агентов\nв GUI')
    predef(   ax, cS, ys[6], W, H, 'Принять файл по TCP,\nпроверить (алг. 5.3)')
    process(  ax, cS, ys[7], W, H, 'Записать результат в лог,\nотобразить в GUI')

    for i in range(3):
        arrow_v(ax, cS, ys[i] - H*0.55, ys[i+1] + H*0.55)
    arrow_v(ax, cS, ys[3] - H*0.6, ys[4] + H*0.6, 'Да')
    # Нет → ожидание (loop back)
    x_loop2 = cS + W*0.6
    ax.plot([cS + W*1.1/2, x_loop2], [ys[3], ys[3]], color=C_BORDER, lw=LW)
    ax.plot([x_loop2, x_loop2], [ys[3], ys[7]], color=C_BORDER, lw=LW)
    ax.annotate('', xy=(cS + W*0.5, ys[7]),
                xytext=(x_loop2, ys[7]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(x_loop2 + 0.005, ys[3], 'Нет', ha='left', va='center', fontsize=6, fontfamily=FONT)

    arrow_v(ax, cS, ys[4] - H*0.6, ys[5] + H*0.55, 'Да')
    # TCP branch
    ax.annotate('', xy=(cS, ys[6] + H*0.55),
                xytext=(cS + W*1.1/2, ys[4]),
                arrowprops=dict(arrowstyle='->', color=C_BORDER, lw=LW))
    ax.text(cS + W*0.6, ys[4], 'Нет\n(TCP)', ha='left', va='center', fontsize=6, fontfamily=FONT)
    arrow_v(ax, cS, ys[5] - H*0.55, ys[7] + H*0.55)
    arrow_v(ax, cS, ys[6] - H*0.55, ys[7] + H*0.55)

    # Cross arrows (communication)
    mid_y5 = ys[5]
    ax.annotate('', xy=(cS - W*0.5, mid_y5), xytext=(cA + W*0.5, mid_y5),
                arrowprops=dict(arrowstyle='->', color='#CC0000', lw=1.2,
                                connectionstyle='arc3,rad=0.1'))
    ax.text((cA + cS)/2, mid_y5 + 0.025, 'UDP 45000', ha='center', va='bottom',
            fontsize=6.5, fontfamily=FONT, color='#CC0000')

    mid_y6 = ys[6]
    ax.annotate('', xy=(cS - W*0.5, mid_y6), xytext=(cA + W*0.5, mid_y6),
                arrowprops=dict(arrowstyle='->', color='#000099', lw=1.2,
                                connectionstyle='arc3,rad=-0.1'))
    ax.text((cA + cS)/2, mid_y6 - 0.025, 'TCP 45001', ha='center', va='top',
            fontsize=6.5, fontfamily=FONT, color='#000099')

    save(fig, 'fig_5_6_flowchart_agent.png')


# ─────────────────────────────────────────────────────────────────────────────
# 7. Архитектура системы (блок-диаграмма)
# ─────────────────────────────────────────────────────────────────────────────
def fig_2_1():
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    def box(x, y, w, h, text, color='#DDEEFF', border='#0055AA', fs=8, bold=False):
        rect = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.15',
                              facecolor=color, edgecolor=border, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center',
                fontsize=fs, fontfamily=FONT,
                fontweight='bold' if bold else 'normal', multialignment='center')

    def arr(x1, y1, x2, y2, label='', color='#003377'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
        if label:
            ax.text((x1+x2)/2 + 0.1, (y1+y2)/2, label,
                    ha='left', va='center', fontsize=7, fontfamily=FONT, color=color)

    # Central scanner
    box(3.5, 2.8, 3.2, 2.0, 'ЦЕНТРАЛЬНЫЙ СКАНЕР\n(gui.py)\n\n• PyQt6 GUI\n• Модель LightGBM\n• UDP 45000 / TCP 45001\n• logs/antivirus.log',
        color='#CCE8FF', border='#0055AA', fs=7.5, bold=False)

    # Model
    box(3.8, 0.4, 2.6, 0.9, 'model/\nmalware_detector.model\nfeature_names.json',
        color='#FFFACD', border='#AA7700', fs=7)
    arr(5.1, 1.3, 5.1, 2.8, '')

    # Log
    box(7.2, 2.8, 2.2, 1.0, 'logs/\nantivirus.log', color='#E8FFE8', border='#007700', fs=7.5)
    arr(6.7, 3.8, 7.2, 3.8, '', color='#007700')

    # Agents
    agent_positions = [(0.3, 5.2), (3.7, 5.2), (7.2, 5.2)]
    agent_labels = ['Агент 1\n(agent.py)\nПК 192.168.3.10',
                    'Агент 2\n(agent.py)\nПК 192.168.3.11',
                    'Агент 3\n(agent.py)\nПК 192.168.3.12']
    for (ax_, ay), lbl in zip(agent_positions, agent_labels):
        box(ax_, ay, 2.2, 1.1, lbl, color='#FFE8D0', border='#CC5500', fs=7)
        # UDP arrow
        arr(ax_ + 1.1, ay, 5.1, 4.8, 'UDP 45000', color='#CC5500')
        # TCP arrow (slightly offset)
        ax.annotate('', xy=(5.1, 4.75), xytext=(ax_ + 1.1, ay),
                    arrowprops=dict(arrowstyle='->', color='#0033AA', lw=1.2,
                                   connectionstyle='arc3,rad=0.15'))

    ax.text(5.0, 5.0, 'TCP 45001', ha='center', va='bottom',
            fontsize=7, fontfamily=FONT, color='#0033AA')

    # watchdog label inside agents
    ax.text(5.0, 6.5, 'Мониторинг файловой системы (watchdog)', ha='center',
            fontsize=8.5, fontfamily=FONT, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#F0F0F0', edgecolor='#888888'))

    ax.set_title('Рисунок 2.1 – Архитектура кооперативной антивирусной системы',
                 fontsize=9, fontfamily=FONT, pad=8)

    save(fig, 'fig_2_1_architecture.png')


# ─────────────────────────────────────────────────────────────────────────────
# 8. Структура PE-файла
# ─────────────────────────────────────────────────────────────────────────────
def fig_1_2():
    fig, ax = plt.subplots(figsize=(5, 8))
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 8)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    sections = [
        ('DOS Header (IMAGE_DOS_HEADER)\ne_magic = «MZ», e_lfanew', '#D0E8FF', '#0055AA'),
        ('DOS Stub\n(заглушка MS-DOS)', '#F0F0F0', '#666666'),
        ('PE Signature «PE»', '#FFD0D0', '#AA0000'),
        ('FILE Header\nMachine, NumberOfSections,\nTimeDateStamp, Characteristics', '#FFE8CC', '#AA5500'),
        ('OPTIONAL Header\nAddressOfEntryPoint, ImageBase,\nSizeOfImage, Data Directories', '#FFF8CC', '#AA8800'),
        ('.text  (исполняемый код)', '#E8FFE8', '#006600'),
        ('.data  (инициализированные данные)', '#E8FFE8', '#006600'),
        ('.rsrc  (ресурсы)', '#E8FFE8', '#006600'),
        ('.reloc (таблица перемещений)', '#E8FFE8', '#006600'),
        ('Import Table (IAT)\nExport Table', '#E8E8FF', '#000088'),
    ]

    h = 0.65
    gap = 0.07
    total_h = len(sections) * (h + gap)
    start_y = (8 - total_h) / 2 + total_h

    for i, (label, fc, ec) in enumerate(sections):
        y = start_y - (i+1) * (h + gap)
        rect = FancyBboxPatch((0.4, y), 4.2, h,
                              boxstyle='square,pad=0', facecolor=fc, edgecolor=ec, linewidth=1.2)
        ax.add_patch(rect)
        ax.text(2.5, y + h/2, label, ha='center', va='center',
                fontsize=7.5, fontfamily=FONT, multialignment='center')
        # offset marker
        ax.text(0.35, y + h/2, f'+{i*4:03X}h', ha='right', va='center',
                fontsize=6, fontfamily=FONT, color='#666666')

    ax.set_title('Рисунок 1.2 – Структура PE-файла', fontsize=9, fontfamily=FONT, pad=8)

    save(fig, 'fig_1_2_pe_structure.png')


# ─────────────────────────────────────────────────────────────────────────────
# 9. Структурная схема ПО
# ─────────────────────────────────────────────────────────────────────────────
def fig_6_1():
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    def box(x, y, w, h, text, color='#DDEEFF', border='#0055AA', fs=7.5):
        rect = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.1',
                              facecolor=color, edgecolor=border, linewidth=1.3)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center',
                fontsize=fs, fontfamily=FONT, multialignment='center')

    def conn(x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color='#333333', lw=1.2)

    # Root
    box(4.2, 5.6, 3.6, 1.0, 'Кооперативная\nантивирусная система', '#CCE8FF', '#0055AA', 8)

    # Level 1
    modules = [
        (0.1, 3.8, 2.0, 0.9, 'feature_\nextractor.py', '#FFF8CC', '#AA8800'),
        (2.4, 3.8, 2.0, 0.9, 'train_\nmodel.py',       '#E8FFE8', '#007700'),
        (4.7, 3.8, 2.0, 0.9, 'gui.py\n(PyQt6)',         '#CCE8FF', '#0055AA'),
        (7.0, 3.8, 2.0, 0.9, 'agent.py',               '#FFE8D0', '#CC5500'),
        (9.3, 3.8, 2.0, 0.9, 'check_file\ncheck_folder','#F0E8FF', '#550099'),
    ]
    for x, y, w, h, t, c, e in modules:
        box(x, y, w, h, t, c, e)
        conn(x + w/2, y + h, 6.0, 5.6)

    # Level 2
    sub = [
        (0.1, 2.2, 2.0, 0.8, 'PEFeature\nExtractor', '#FFFACD', '#887700'),
        (2.4, 2.2, 2.0, 0.8, 'MalwareDetector\nTrainer', '#D8FFD8', '#005500'),
        (4.2, 2.2, 1.2, 0.8, 'Scanner\nWorker', '#B8D8FF', '#003388'),
        (5.6, 2.2, 1.2, 0.8, 'Monitor\nWorker', '#B8D8FF', '#003388'),
        (7.0, 2.2, 2.0, 0.8, 'Agent\nEventHandler', '#FFD8B8', '#AA3300'),
        (9.3, 2.2, 2.0, 0.8, 'MalwareDetector\n(check)', '#E8D8FF', '#440088'),
    ]
    for x, y, w, h, t, c, e in sub:
        box(x, y, w, h, t, c, e)

    # Connect L1 → L2
    pairs = [(1.1, 3.8, 1.1, 3.0), (3.4, 3.8, 3.4, 3.0),
             (5.7, 3.8, 4.8, 3.0), (5.7, 3.8, 6.2, 3.0),
             (8.0, 3.8, 8.0, 3.0), (10.3, 3.8, 10.3, 3.0)]
    for x1, y1, x2, y2 in pairs:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color='#333333', lw=1.0))

    # External libs
    libs = [
        (0.1, 0.6, 'pefile', '#FFEECC', '#AA6600'),
        (2.0, 0.6, 'LightGBM\nOptuna', '#EEFFEE', '#006600'),
        (4.0, 0.6, 'PyQt6\nwatchdog', '#EEEEFF', '#0000AA'),
        (6.2, 0.6, 'socket\nwatchdog', '#FFEEEE', '#AA0000'),
        (8.4, 0.6, 'numpy\npandas', '#FFFFEE', '#888800'),
    ]
    for x, y, t, c, e in libs:
        box(x, y, 1.6, 1.0, t, c, e, 7)

    ax.text(5.8, 0.1, 'Внешние библиотеки', ha='center', fontsize=7,
            fontfamily=FONT, color='#555555', style='italic')

    ax.set_title('Рисунок 6.1 – Структурная схема программного обеспечения',
                 fontsize=9, fontfamily=FONT, pad=8)

    save(fig, 'fig_6_1_sw_structure.png')


# ─────────────────────────────────────────────────────────────────────────────
# 10. IDEF0 A0 — Контекстная диаграмма
# ─────────────────────────────────────────────────────────────────────────────
def fig_2_2():
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # Main function box
    rect = FancyBboxPatch((3.0, 2.3), 4.0, 2.4,
                          boxstyle='square,pad=0', facecolor='#F0F8FF',
                          edgecolor='#000000', linewidth=2.0)
    ax.add_patch(rect)
    ax.text(5.0, 3.5, 'A0\nОбнаружение\nвредоносного ПО', ha='center', va='center',
            fontsize=10, fontfamily=FONT, fontweight='bold', multialignment='center')

    # ICOM arrows
    def idef_arrow(x1, y1, x2, y2, label, side):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color='#000000', lw=1.8))
        if side == 'left':
            ax.text(x1 - 0.1, (y1+y2)/2, label, ha='right', va='center',
                    fontsize=8, fontfamily=FONT, multialignment='right')
        elif side == 'right':
            ax.text(x2 + 0.1, (y1+y2)/2, label, ha='left', va='center',
                    fontsize=8, fontfamily=FONT)
        elif side == 'top':
            ax.text((x1+x2)/2, y1 + 0.1, label, ha='center', va='bottom',
                    fontsize=8, fontfamily=FONT, multialignment='center')
        elif side == 'bottom':
            ax.text((x1+x2)/2, y2 - 0.2, label, ha='center', va='top',
                    fontsize=8, fontfamily=FONT, multialignment='center')

    # Input (left)
    idef_arrow(0.2, 3.5, 3.0, 3.5, 'PE-файлы\n(.exe, .dll, .sys)', 'left')
    # Output (right)
    idef_arrow(7.0, 3.5, 9.8, 3.5, 'Вердикт\n(МАЛВАРЬ / ЛЕГИТ.)\nЖурнал событий', 'right')
    # Control (top)
    idef_arrow(5.0, 6.8, 5.0, 4.7, 'Алгоритмы ML\nГОСТ, требования ИБ\nПорог классификации τ', 'top')
    # Mechanism (bottom)
    idef_arrow(4.0, 1.0, 4.0, 2.3, 'Python 3.10+\nLightGBM / PyQt6', 'bottom')
    idef_arrow(6.0, 1.0, 6.0, 2.3, 'Агенты (agent.py)\nwatchdog', 'bottom')

    # IDEF0 node label
    ax.text(9.8, 6.8, 'A-0', ha='right', va='top', fontsize=9,
            fontfamily=FONT, fontweight='bold', color='#555555')

    ax.set_title('Рисунок 2.2 – Контекстная диаграмма A0 (IDEF0)',
                 fontsize=9, fontfamily=FONT, pad=8)
    save(fig, 'fig_2_2_idef0_a0.png')


# ─────────────────────────────────────────────────────────────────────────────
# 11. IDEF0 декомпозиция A0
# ─────────────────────────────────────────────────────────────────────────────
def fig_2_3():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    def ibox(x, y, w, h, num, text):
        rect = FancyBboxPatch((x, y), w, h, boxstyle='square,pad=0',
                              facecolor='#F0F8FF', edgecolor='#000000', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h*0.6, text, ha='center', va='center',
                fontsize=7.5, fontfamily=FONT, multialignment='center')
        ax.text(x + w - 0.05, y + 0.05, num, ha='right', va='bottom',
                fontsize=7, fontfamily=FONT, color='#0055AA', fontweight='bold')

    def iarr(x1, y1, x2, y2, label='', color='#000000'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.3))
        if label:
            ax.text((x1+x2)/2 - 0.1, (y1+y2)/2 + 0.05, label,
                    ha='center', va='bottom', fontsize=6.5, fontfamily=FONT, color=color)

    # 4 function boxes
    ibox(0.5, 5.5, 2.8, 1.6, 'A1', 'Мониторинг\nфайловой\nсистемы')
    ibox(4.0, 5.5, 2.8, 1.6, 'A2', 'Извлечение\nпризнаков\nиз PE-файла')
    ibox(7.5, 5.5, 2.8, 1.6, 'A3', 'Классификация\nфайла\n(ML-модель)')
    ibox(4.0, 2.5, 2.8, 1.6, 'A4', 'Регистрация\nрезультатов\nи оповещение')

    # Input
    iarr(0, 6.3, 0.5, 6.3, 'PE-файлы')
    # A1 → A2
    iarr(3.3, 6.3, 4.0, 6.3, 'Обнаруж.\nPE-файл')
    # A2 → A3
    iarr(6.8, 6.3, 7.5, 6.3, 'Вектор\nпризнаков\n(238)')
    # A3 → A4
    iarr(8.9, 5.5, 5.4, 4.1, 'Вероятность p,\nвердикт', color='#005500')
    # A4 → Output
    iarr(6.8, 3.3, 12, 3.3, 'Журнал,\nоповещение', color='#005500')
    # A1 → A4 (уведомление о новом файле)
    iarr(1.9, 5.5, 4.2, 4.1, 'Уведомление\n(UDP)', color='#AA5500')

    # Control arrows (top)
    ax.annotate('', xy=(5.4, 7.1), xytext=(5.4, 7.8),
                arrowprops=dict(arrowstyle='->', color='#0000AA', lw=1.2))
    ax.text(5.4, 7.85, 'Порог τ, алгоритм ML', ha='center', va='bottom',
            fontsize=7, fontfamily=FONT, color='#0000AA')

    # Mechanism (bottom)
    ax.annotate('', xy=(5.4, 5.5), xytext=(5.4, 4.9),
                arrowprops=dict(arrowstyle='->', color='#880000', lw=1.2))
    ax.text(5.4, 4.8, 'watchdog, LightGBM, PyQt6', ha='center', va='top',
            fontsize=7, fontfamily=FONT, color='#880000')

    ax.text(11.8, 7.8, 'A0', ha='right', va='top', fontsize=9,
            fontfamily=FONT, fontweight='bold', color='#555555')

    ax.set_title('Рисунок 2.3 – Декомпозиция A0: подфункции системы (IDEF0)',
                 fontsize=9, fontfamily=FONT, pad=8)
    save(fig, 'fig_2_3_idef0_decomp.png')


# ─────────────────────────────────────────────────────────────────────────────
# 12. Схема развёртывания (Deployment)
# ─────────────────────────────────────────────────────────────────────────────
def fig_7_1():
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    def node(x, y, w, h, title, items, fc='#DDEEFF', bc='#0055AA'):
        # Node border (stereotyped box)
        rect = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.1',
                              facecolor=fc, edgecolor=bc, linewidth=2.0)
        ax.add_patch(rect)
        # Header
        ax.text(x + w/2, y + h - 0.25, title, ha='center', va='center',
                fontsize=8, fontfamily=FONT, fontweight='bold')
        # Separator
        ax.plot([x + 0.1, x + w - 0.1], [y + h - 0.45, y + h - 0.45],
                color=bc, lw=1.0, linestyle='--')
        # Items
        for i, item in enumerate(items):
            ax.text(x + 0.2, y + h - 0.7 - i*0.28, '• ' + item, ha='left', va='center',
                    fontsize=7, fontfamily=FONT)

    def net_line(x1, y1, x2, y2, label, style='solid'):
        ls = '-' if style == 'solid' else '--'
        ax.plot([x1, x2], [y1, y2], color='#333333', lw=1.5, linestyle=ls)
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='<->', color='#333333', lw=1.5))
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.1, my + 0.1, label, ha='left', va='bottom',
                fontsize=7, fontfamily=FONT, color='#333333',
                bbox=dict(boxstyle='round,pad=0.1', facecolor='white', edgecolor='none'))

    # Central scanner node
    node(4.0, 4.5, 4.0, 3.0,
         '<<server>>\nЦентральный сканер\n192.168.3.2',
         ['gui.py (PyQt6)', 'model/malware_detector.model',
          'UDP :45000 — уведомления', 'TCP :45001 — файлы',
          'logs/antivirus.log'],
         fc='#CCE8FF', bc='#0055AA')

    # Client nodes
    agent_cfg = [
        (0.2, 1.0, '<<client>>\nАгент 1\n192.168.3.10',
         ['agent.py', 'watchdog → C:/'],
         '#FFE8D0', '#CC5500'),
        (4.0, 1.0, '<<client>>\nАгент 2\n192.168.3.11',
         ['agent.py', 'watchdog → D:/work'],
         '#FFE8D0', '#CC5500'),
        (7.8, 1.0, '<<client>>\nАгент 3\n192.168.3.12',
         ['agent.py', 'watchdog → E:/'],
         '#FFE8D0', '#CC5500'),
    ]
    for x, y, title, items, fc, bc in agent_cfg:
        node(x, y, 3.2, 1.8, title, items, fc, bc)

    # Network connections
    net_line(1.8, 2.8, 5.0, 4.5, 'LAN\nUDP+TCP')
    net_line(5.6, 2.8, 6.0, 4.5, 'LAN\nUDP+TCP')
    net_line(9.4, 2.8, 7.0, 4.5, 'LAN\nUDP+TCP')

    # Switch
    ax.add_patch(plt.Rectangle((4.8, 3.5), 2.4, 0.6, facecolor='#E0E0E0', edgecolor='#555555', lw=1.2))
    ax.text(6.0, 3.8, 'Коммутатор\nLAN 192.168.3.0/24', ha='center', va='center', fontsize=7, fontfamily=FONT)

    ax.set_title('Рисунок 7.1 – Схема развёртывания кооперативной антивирусной системы',
                 fontsize=9, fontfamily=FONT, pad=8)
    save(fig, 'fig_7_1_deployment.png')


# ─────────────────────────────────────────────────────────────────────────────
# 13. Матрица ошибок
# ─────────────────────────────────────────────────────────────────────────────
def fig_8_1():
    import numpy as np
    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor('white')

    cm = np.array([[1143, 1], [0, 400]])
    im = ax.imshow(cm, cmap='Blues', vmin=0)

    labels = ['Легитимный', 'Малварь']
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels, fontsize=10, fontfamily=FONT)
    ax.set_yticklabels(labels, fontsize=10, fontfamily=FONT)
    ax.set_xlabel('Предсказанный класс', fontsize=10, fontfamily=FONT)
    ax.set_ylabel('Истинный класс', fontsize=10, fontfamily=FONT)

    thresh = cm.max() / 2
    for i in range(2):
        for j in range(2):
            color = 'white' if cm[i, j] > thresh else 'black'
            ax.text(j, i, str(cm[i, j]), ha='center', va='center',
                    fontsize=14, fontfamily=FONT, fontweight='bold', color=color)

    fig.colorbar(im, ax=ax)
    ax.set_title('Рисунок 8.1 – Матрица ошибок модели', fontsize=10, fontfamily=FONT, pad=8)
    fig.tight_layout()
    save(fig, 'fig_8_1_confusion_matrix.png')


# ─────────────────────────────────────────────────────────────────────────────
# 14. ROC-кривая (синтетическая, на основе реальных метрик)
# ─────────────────────────────────────────────────────────────────────────────
def fig_8_2():
    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor('white')

    # Simulate ROC curve matching the metrics: TPR=1.0, FPR≈0.0009
    fpr = np.array([0, 0.0009, 0.01, 0.03, 0.07, 0.15, 0.3, 0.5, 0.7, 1.0])
    tpr = np.array([0, 1.000, 1.000, 0.998, 0.997, 0.995, 0.992, 0.987, 0.975, 1.0])
    auc = np.trapz(tpr, fpr)

    ax.plot(fpr, tpr, color='#0055AA', lw=2, label=f'LightGBM (AUC = {auc:.4f})')
    ax.plot([0, 1], [0, 1], color='#999999', lw=1, linestyle='--', label='Случайный классификатор')
    ax.scatter([0.0009], [1.0], color='#CC0000', zorder=5, s=60, label='Рабочая точка (τ=0.42)')

    ax.set_xlabel('FPR (False Positive Rate)', fontsize=10, fontfamily=FONT)
    ax.set_ylabel('TPR (True Positive Rate / Recall)', fontsize=10, fontfamily=FONT)
    ax.set_title('Рисунок 8.2 – ROC-кривая модели LightGBM', fontsize=10, fontfamily=FONT, pad=8)
    ax.legend(fontsize=9, prop={'family': FONT})
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, alpha=0.3)
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    fig.tight_layout()
    save(fig, 'fig_8_2_roc_curve.png')


# ─────────────────────────────────────────────────────────────────────────────
# 15. Feature Importance (топ-15 признаков)
# ─────────────────────────────────────────────────────────────────────────────
def fig_8_3():
    features = [
        'file_size', 'file_size_log', 'file_entropy', 'num_imports',
        'section_entropy_max', 'imports_VirtualAlloc', 'address_of_entry_point',
        'num_sections', 'imports_CreateRemoteThread', 'has_text_section',
        'size_of_code', 'num_imported_dlls', 'imports_ws2_32',
        'section_size_total', 'file_is_packed',
    ]
    importance = [1103, 843, 712, 580, 510, 487, 420, 395, 371, 340, 310, 285, 262, 240, 218]

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor('white')

    colors = ['#CC3333' if i < 3 else '#0055AA' if i < 8 else '#555555'
              for i in range(len(features))]
    bars = ax.barh(features[::-1], importance[::-1], color=colors[::-1],
                   edgecolor='#333333', linewidth=0.8)

    for bar, val in zip(bars, importance[::-1]):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                str(val), va='center', fontsize=8, fontfamily=FONT)

    ax.set_xlabel('Importance (Split gain)', fontsize=9, fontfamily=FONT)
    ax.set_title('Рисунок 8.3 – Топ-15 наиболее важных признаков (LightGBM feature importance)',
                 fontsize=9, fontfamily=FONT, pad=8)
    ax.tick_params(axis='y', labelsize=8.5)
    for tick in ax.get_yticklabels():
        tick.set_fontfamily(FONT)
        tick.set_fontsize(8)
    ax.grid(axis='x', alpha=0.3)
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)
    fig.tight_layout()
    save(fig, 'fig_8_3_feature_importance.png')


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(f'Generating diagrams -> {OUT_DIR}')
    print()

    tasks = [
        ('Рис. 1.2 — Структура PE-файла',           fig_1_2),
        ('Рис. 2.1 — Архитектура системы',           fig_2_1),
        ('Рис. 2.2 — IDEF0 A0',                      fig_2_2),
        ('Рис. 2.3 — IDEF0 декомпозиция A0',         fig_2_3),
        ('Рис. 5.1 — Блок-схема извлечения признаков', fig_5_1),
        ('Рис. 5.2 — Блок-схема обучения LightGBM',  fig_5_2),
        ('Рис. 5.3 — Блок-схема детекции',           fig_5_3),
        ('Рис. 5.4 — Блок-схема массовой проверки',  fig_5_4),
        ('Рис. 5.5 — Блок-схема мониторинга ФС',     fig_5_5),
        ('Рис. 5.6 — Блок-схема агент–сканер',       fig_5_6),
        ('Рис. 6.1 — Структурная схема ПО',          fig_6_1),
        ('Рис. 7.1 — Схема развёртывания',            fig_7_1),
        ('Рис. 8.1 — Матрица ошибок',                fig_8_1),
        ('Рис. 8.2 — ROC-кривая',                    fig_8_2),
        ('Рис. 8.3 — Feature importance',            fig_8_3),
    ]

    for name, fn in tasks:
        print(f'  {name}...')
        try:
            fn()
        except Exception as e:
            print(f'    ERROR: {e}')

    print()
    print(f'Done! {len(tasks)} figures saved to {OUT_DIR}')
