# Кооперативная антивирусная система с интеллектуальным механизмом детекции

Система антивирусной защиты корпоративной сети на основе статического анализа PE-файлов и машинного обучения (LightGBM). Реализует кооперативное сканирование — несколько агентов работают параллельно и пишут в общий лог с идентификацией компьютера.

## Структура проекта

```
WKR/
├── src/
│   ├── gui.py                  # Основной GUI (PyQt6) — точка входа
│   ├── agent.py                # Агент для клиентских ПК
│   ├── feature_extractor.py    # Извлечение признаков из PE-файлов
│   ├── check_file.py           # Консольная проверка одного файла
│   ├── check_folder.py         # Консольная проверка папки
│   ├── train_model.py          # Обучение модели LightGBM
│   └── evaluate_model.py       # Оценка качества модели
│
├── model/
│   ├── malware_detector.model  # Обученная модель LightGBM
│   ├── feature_names.json      # Список признаков
│   └── threshold.json          # Оптимальный порог детекции
│
├── scripts/
│   ├── collect_benign_samples.py      # Сбор легитимных PE из Windows
│   └── generate_patterned_malware.py  # Генерация синтетической малвари
│
├── data/
│   ├── malware/                # Образцы малвари для обучения
│   └── benign/                 # Легитимные файлы для обучения
│
├── logs/
│   └── antivirus.log           # Общий лог сканирований
│
├── docs/                       # Техническая документация
├── fonts/                      # Шрифты GUI (Inter, JetBrains Mono)
├── assets/                     # Ресурсы (scanning.gif)
├── config/                     # Настройки (monitor_path.txt)
├── files_to_check/             # Тестовые файлы для ручной проверки
└── requirements.txt
```

## Быстрый старт

### Первый запуск на новом ПК

Просто запустить `setup_and_run.bat` — он сделает всё автоматически:
- Проверит Python
- Создаст виртуальное окружение
- Установит все зависимости
- Обучит модель если её нет
- Запустит GUI

```
setup_and_run.bat
```

> Требуется Python 3.10+ с сайта [python.org](https://python.org). При установке отметить **"Add Python to PATH"**.

### Запуск GUI (повторный)

```bash
python src/gui.py
# или
run_gui.bat
```

### Консольная проверка файлов

```bash
# Один файл
python src/check_file.py suspicious.exe

# Папка с файлами
python src/check_folder.py files_to_check

# С сохранением результатов
python src/check_folder.py files_to_check --output results.json
```

### Запуск агента (на клиентском ПК)

```bash
python src/agent.py --server 192.168.3.2 --watch "C:/"
```

## Обучение модели

### Подготовка датасета

```bash
# Сбор легитимных файлов из Windows
python scripts/collect_benign_samples.py --output data/benign --max-files 500

# Генерация синтетической малвари (8 типов по 250 образцов)
python scripts/generate_patterned_malware.py --output data/malware --samples 250 --pattern trojan
python scripts/generate_patterned_malware.py --output data/malware --samples 250 --pattern ransomware
# ... и остальные типы: rootkit, backdoor, keylogger, packed, stealer, banking
```

### Запуск обучения

```bash
# Базовое обучение
python src/train_model.py --malware-dir data/malware --benign-dir data/benign

# Полный пайплайн с CV и подбором гиперпараметров на GPU
python src/train_model.py \
  --malware-dir data/malware \
  --benign-dir data/benign \
  --cv-folds 5 \
  --tune --tune-trials 50 \
  --use-gpu
```

### Параметры обучения

| Параметр | По умолчанию | Описание |
|---|---|---|
| `--cv-folds` | 5 | Количество фолдов кросс-валидации (0 — отключить) |
| `--tune` | выкл | Подбор гиперпараметров через Optuna |
| `--tune-trials` | 50 | Количество триалов Optuna |
| `--use-gpu` | выкл | Обучение на GPU (OpenCL) |
| `--num-boost-round` | 1000 | Максимум итераций бустинга |
| `--test-size` | 0.2 | Доля тестовой выборки |

## Технические детали

- **Язык:** Python 3.10+
- **GUI:** PyQt6
- **Модель:** LightGBM с автоподбором гиперпараметров (Optuna)
- **Признаки:** 238+ статических признаков PE-файлов
  - Заголовки DOS/FILE/OPTIONAL
  - Секции (размер, энтропия, флаги)
  - Импорты и экспорты
  - Ресурсы
  - Строки (подозрительные паттерны)
  - Энтропия файла целиком (детекция упаковщиков)
- **Агентная сеть:** UDP 45000 (события) + TCP 45001 (передача файлов)
- **GPU:** RTX 5070, поддержка через `--use-gpu`

## Зависимости

```bash
pip install -r requirements.txt
```

Основные: `PyQt6`, `lightgbm`, `pefile`, `scikit-learn`, `pandas`, `numpy`, `optuna`, `watchdog`, `tqdm`

## Дополнительная документация

- [docs/ALGORITHMS_REPORT.md](docs/ALGORITHMS_REPORT.md) — описание алгоритмов
- [docs/QUICKSTART.md](docs/QUICKSTART.md) — быстрое руководство
- [docs/SAFE_MALWARE_SOURCES.md](docs/SAFE_MALWARE_SOURCES.md) — источники датасетов
- [docs/TRAINING_RESULTS.md](docs/TRAINING_RESULTS.md) — результаты обучения
