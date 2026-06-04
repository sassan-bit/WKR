"""
Скрипт для обучения модели детекции малвари на основе статических признаков PE-файлов.
Поддерживает работу с датасетом EMBER и собственными данными.
"""

import os
import json
import time
import pickle
import platform
import warnings
import subprocess
import multiprocessing
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, fbeta_score, roc_auc_score, classification_report, confusion_matrix
import lightgbm as lgb
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))
from feature_extractor import PEFeatureExtractor
from tqdm import tqdm
import argparse


def format_duration(seconds: float) -> str:
    """Форматирует длительность в человекочитаемый вид."""
    if seconds < 60:
        return f"{seconds:.1f} сек"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)} мин {sec:.0f} сек"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)} ч {int(minutes)} мин {sec:.0f} сек"


def get_gpu_info():
    """
    Возвращает список словарей с информацией о видеокартах NVIDIA.
    Использует nvidia-smi. Если недоступен — возвращает пустой список.
    """
    gpus = []
    try:
        output = subprocess.check_output(
            ['nvidia-smi',
             '--query-gpu=name,memory.total,driver_version',
             '--format=csv,noheader,nounits'],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10
        )
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                gpus.append({
                    'name': parts[0],
                    'memory_mb': parts[1],
                    'driver': parts[2],
                })
    except Exception:
        pass
    return gpus
        

def print_system_info():
    """Выводит информацию о системе и доступных видеокартах."""
    print("=" * 60)
    print("ИНФОРМАЦИЯ О СИСТЕМЕ")
    print("=" * 60)
    print(f"ОС:           {platform.system()} {platform.release()}")
    print(f"Процессор:    {platform.processor() or 'неизвестно'}")
    print(f"Ядер CPU:     {os.cpu_count()}")
    print(f"Python:       {platform.python_version()}")
    print(f"LightGBM:     {lgb.__version__}")

    gpus = get_gpu_info()
    if gpus:
        for i, gpu in enumerate(gpus):
            print(f"GPU #{i}:       {gpu['name']} "
                  f"({gpu['memory_mb']} MB, драйвер {gpu['driver']})")
    else:
        print("GPU:          не обнаружено (nvidia-smi недоступен)")
    print("=" * 60)


def check_gpu_support():
    """Проверяет, доступен ли GPU для LightGBM (реальным тестовым обучением)."""
    try:
        # Пробуем обучить минимальную модель на GPU
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'device': 'gpu',
            'gpu_platform_id': 0,
            'gpu_device_id': 0,
            'verbosity': -1,
            'num_leaves': 3,
        }
        X = np.random.rand(10, 4).astype(np.float32)
        y = np.array([0, 1] * 5)
        train_data = lgb.Dataset(X, label=y)
        lgb.train(params, train_data, num_boost_round=1)
        return True
    except Exception:
        return False


class TqdmProgressCallback:
    """Колбэк для LightGBM, отображающий прогресс обучения через tqdm."""

    def __init__(self, total_rounds: int):
        self.pbar = tqdm(total=total_rounds, desc="Бустинг", unit="итер")

    def __call__(self, env):
        # env.iteration — текущая итерация (0-based)
        self.pbar.update(1)
        # Показываем текущую метрику в баре, если есть
        if env.evaluation_result_list:
            try:
                # последний элемент — обычно валидационная метрика
                _, metric_name, metric_value, _ = env.evaluation_result_list[-1]
                self.pbar.set_postfix({metric_name: f"{metric_value:.5f}"})
            except (ValueError, IndexError):
                pass

    def close(self):
        if self.pbar is not None:
            self.pbar.close()
            self.pbar = None


def _extract_one(file_path: str) -> tuple:
    """Извлекает признаки из одного файла. Функция верхнего уровня для multiprocessing."""
    from feature_extractor import PEFeatureExtractor
    fe = PEFeatureExtractor()
    features = fe.extract_features(file_path)
    return (file_path, features)


class MalwareDetectorTrainer:
    """Класс для обучения модели детекции малвари."""
    
    def __init__(self, model_type='lightgbm'):
        self.model_type = model_type
        self.model = None
        self.feature_extractor = PEFeatureExtractor()
        self.feature_names = []
    
    def load_ember_dataset(self, ember_dir: str):
        """
        Загружает датасет EMBER (если доступен).
        EMBER уже содержит извлеченные признаки в формате векторов.
        """
        try:
            # EMBER формат: X_train, y_train, X_test, y_test в формате .dat
            train_path = os.path.join(ember_dir, 'X_train.dat')
            train_labels_path = os.path.join(ember_dir, 'y_train.dat')
            test_path = os.path.join(ember_dir, 'X_test.dat')
            test_labels_path = os.path.join(ember_dir, 'y_test.dat')
            
            if not all(os.path.exists(p) for p in [train_path, train_labels_path]):
                print("EMBER датасет не найден. Используйте метод extract_features_from_directory.")
                return None, None, None, None
            
            print("Загрузка EMBER датасета...")
            
            # EMBER использует 2381 признак
            num_features = 2381
            
            # Загрузка данных
            X_train = np.memmap(train_path, dtype=np.float32, mode='r')
            y_train = np.memmap(train_labels_path, dtype=np.uint8, mode='r')
            X_test = np.memmap(test_path, dtype=np.float32, mode='r')
            y_test = np.memmap(test_labels_path, dtype=np.uint8, mode='r')
            
            # Преобразование в массивы и решейп
            X_train = np.array(X_train).reshape(-1, num_features)
            y_train = np.array(y_train)
            X_test = np.array(X_test).reshape(-1, num_features)
            y_test = np.array(y_test)
            
            # Фильтрация неразмеченных образцов (label = -1 в EMBER)
            train_mask = y_train != 255  # EMBER использует 255 для неразмеченных
            test_mask = y_test != 255
            
            X_train = X_train[train_mask]
            y_train = y_train[train_mask]
            X_test = X_test[test_mask]
            y_test = y_test[test_mask]
            
            # Нормализация меток (EMBER: 0=benign, 1=malware)
            # Наша модель: 0=benign, 1=malware (совпадает)
            
            print(f"Загружено: Train={len(X_train)}, Test={len(X_test)}")
            print(f"  Train: Малварь={np.sum(y_train)}, Легитимные={len(y_train)-np.sum(y_train)}")
            print(f"  Test: Малварь={np.sum(y_test)}, Легитимные={len(y_test)-np.sum(y_test)}")
            
            # Создаем фиктивные имена признаков для совместимости
            self.feature_names = [f'feature_{i}' for i in range(num_features)]
            
            return X_train, y_train, X_test, y_test
            
        except Exception as e:
            print(f"Ошибка при загрузке EMBER: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None, None
    
    def extract_features_from_directory(self, malware_dir: str, benign_dir: str, 
                                        max_samples_per_class: int = None):
        """
        Извлекает признаки из PE-файлов в указанных директориях.
        
        Args:
            malware_dir: Директория с малварью
            benign_dir: Директория с легитимными файлами
            max_samples_per_class: Максимальное количество образцов на класс
        """
        workers = max(1, (os.cpu_count() or 4) - 1)
        print(f"Извлечение признаков из PE-файлов (параллельно, {workers} ядер)...")
        extract_start = time.perf_counter()

        all_features = []
        all_labels = []

        def _process_dir(directory, label, desc):
            files = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if f.lower().endswith(('.exe', '.dll', '.sys'))
            ]
            if max_samples_per_class:
                files = files[:max_samples_per_class]

            with multiprocessing.Pool(processes=workers) as pool:
                for _, features in tqdm(
                    pool.imap_unordered(_extract_one, files),
                    total=len(files), desc=desc
                ):
                    if features:
                        all_features.append(features)
                        all_labels.append(label)

        if malware_dir and os.path.exists(malware_dir):
            _process_dir(malware_dir, 1, "Малварь")

        if benign_dir and os.path.exists(benign_dir):
            _process_dir(benign_dir, 0, "Легитимные")
        
        if not all_features:
            raise ValueError("Не удалось извлечь признаки из файлов!")
        
        # Преобразование в DataFrame для удобства
        df = pd.DataFrame(all_features)
        self.feature_names = list(df.columns)
        
        # Заполнение пропущенных значений
        df = df.fillna(0)
        
        # Удаление нечисловых колонок (хеши)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        df = df[numeric_cols]
        self.feature_names = numeric_cols
        
        X = df.values
        y = np.array(all_labels)
        
        extract_elapsed = time.perf_counter() - extract_start
        print(f"Извлечено признаков: {len(self.feature_names)}")
        print(f"Всего образцов: {len(X)} (Малварь: {np.sum(y)}, Легитимные: {len(y) - np.sum(y)})")
        print(f"Время извлечения признаков: {format_duration(extract_elapsed)}")
        
        return X, y
    
    def _build_params(self, use_gpu: bool, gpu_available: bool):
        """Формирует параметры LightGBM с учётом устройства (CPU/GPU)."""
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': 42,
            'num_threads': os.cpu_count() or 0,
        }

        if use_gpu and gpu_available:
            # Параметры для максимального использования GPU
            params.update({
                'device': 'gpu',
                'gpu_platform_id': 0,
                'gpu_device_id': 0,
                # На GPU быстрее работает 256-битная гистограмма по single precision
                'gpu_use_dp': False,            # single precision — быстрее
                'max_bin': 63,                  # GPU оптимально с max_bin <= 63
            })
        return params

    def train(self, X_train, y_train, X_val=None, y_val=None, 
              params=None, num_boost_round=1000, use_gpu=False):
        """
        Обучает модель LightGBM.
        
        Args:
            X_train: Признаки обучающей выборки
            y_train: Метки обучающей выборки
            X_val: Признаки валидационной выборки (опционально)
            y_val: Метки валидационной выборки (опционально)
            params: Параметры LightGBM (если None — формируются автоматически)
            num_boost_round: Количество итераций бустинга
            use_gpu: Использовать GPU для обучения (с fallback на CPU)
        """
        gpu_available = False
        if use_gpu:
            print("Проверка доступности GPU для LightGBM...")
            gpu_available = check_gpu_support()
            if gpu_available:
                print(">>> Обучение будет выполнено на GPU (видеокарте).")
            else:
                print(">>> GPU не доступен для LightGBM. Обучение на CPU.")
        else:
            print(">>> Обучение модели LightGBM на CPU.")

        if params is None:
            params = self._build_params(use_gpu, gpu_available)

        # Коррекция дисбаланса классов (если не задана вручную через tune)
        n_benign  = int(np.sum(y_train == 0))
        n_malware = int(np.sum(y_train == 1))
        if 'scale_pos_weight' not in params:
            ratio = n_benign / n_malware if n_malware > 0 else 1.0
            params['scale_pos_weight'] = ratio
        else:
            ratio = params['scale_pos_weight']
        print(f"Баланс классов: легитимных={n_benign}, малварь={n_malware}, "
              f"scale_pos_weight={ratio:.2f}")

        # Приведение к float32 ускоряет передачу данных на GPU и экономит память
        X_train = np.ascontiguousarray(X_train, dtype=np.float32)
        if X_val is not None:
            X_val = np.ascontiguousarray(X_val, dtype=np.float32)

        # Создание датасетов LightGBM
        train_data = lgb.Dataset(X_train, label=y_train)
        
        valid_sets = [train_data]
        valid_names = ['train']
        
        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            valid_sets.append(val_data)
            valid_names.append('valid')
        
        def _run_training(p):
            progress = TqdmProgressCallback(num_boost_round)
            try:
                model = lgb.train(
                    p,
                    train_data,
                    num_boost_round=num_boost_round,
                    valid_sets=valid_sets,
                    valid_names=valid_names,
                    callbacks=[
                        lgb.early_stopping(stopping_rounds=50, verbose=False),
                        progress,
                    ]
                )
            finally:
                progress.close()
            return model

        device_label = "GPU" if (use_gpu and gpu_available) else "CPU"
        print(f"Старт обучения на {device_label} "
              f"(максимум {num_boost_round} итераций)...")
        start = time.perf_counter()

        # Обучение с fallback на CPU при ошибке GPU
        try:
            self.model = _run_training(params)
        except lgb.basic.LightGBMError as e:
            if use_gpu and gpu_available:
                warnings.warn(f"Ошибка GPU-обучения: {e}. Пробуем на CPU...")
                params = self._build_params(use_gpu=False, gpu_available=False)
                self.model = _run_training(params)
                device_label = "CPU (fallback)"
            else:
                raise

        elapsed = time.perf_counter() - start
        best_iter = getattr(self.model, 'best_iteration', None) or num_boost_round
        print(f"Обучение завершено на {device_label}!")
        print(f"  Время обучения:   {format_duration(elapsed)}")
        print(f"  Лучших итераций:  {best_iter}")
        if best_iter:
            print(f"  Скорость:         {elapsed / best_iter * 1000:.1f} мс/итерация")
    
    def tune_hyperparams(self, X_train, y_train, n_trials: int = 50,
                         use_gpu: bool = False) -> dict:
        """
        Подбирает гиперпараметры LightGBM через Optuna (TPE-сэмплер).
        Оптимизирует F2-score на фиксированном val-сплите.
        Возвращает словарь params для передачи в train().
        """
        try:
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError:
            print("Optuna не установлена: pip install optuna")
            print("Используются параметры по умолчанию.")
            return self._build_params(use_gpu=use_gpu, gpu_available=False)

        gpu_available = check_gpu_support() if use_gpu else False
        base_params = self._build_params(use_gpu=use_gpu, gpu_available=gpu_available)

        X_tr, X_val, y_tr, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
        )
        X_tr  = np.ascontiguousarray(X_tr, dtype=np.float32)
        X_val = np.ascontiguousarray(X_val, dtype=np.float32)

        n_neg = int(np.sum(y_tr == 0))
        n_pos = int(np.sum(y_tr == 1))
        spw = n_neg / n_pos if n_pos > 0 else 1.0

        def objective(trial):
            trial_params = {
                **base_params,
                'num_leaves':        trial.suggest_int('num_leaves', 16, 256),
                'learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'feature_fraction':  trial.suggest_float('feature_fraction', 0.5, 1.0),
                'bagging_fraction':  trial.suggest_float('bagging_fraction', 0.5, 1.0),
                'bagging_freq':      trial.suggest_int('bagging_freq', 1, 10),
                'min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
                'reg_alpha':         trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                'reg_lambda':        trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
                'scale_pos_weight':  spw,
            }

            tr_ds  = lgb.Dataset(X_tr, label=y_tr)
            val_ds = lgb.Dataset(X_val, label=y_val, reference=tr_ds)

            model = lgb.train(
                trial_params,
                tr_ds,
                num_boost_round=300,
                valid_sets=[val_ds],
                valid_names=['val'],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=30, verbose=False),
                    lgb.log_evaluation(period=-1),
                ],
            )

            y_proba = model.predict(X_val)
            y_pred  = (y_proba >= 0.5).astype(int)
            return fbeta_score(y_val, y_pred, beta=2, zero_division=0)

        print(f"\n{'='*55}")
        print(f"ПОДБОР ГИПЕРПАРАМЕТРОВ  (Optuna, {n_trials} триалов)")
        print(f"{'='*55}")

        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

        best = study.best_trial
        print(f"\nЛучший F2-score: {best.value:.4f}")
        print("Лучшие параметры:")
        for k, v in best.params.items():
            print(f"  {k:<22}: {v}")

        best_params = {**base_params, **best.params, 'scale_pos_weight': spw}
        print(f"{'='*55}\n")
        return best_params

    def cross_validate(self, X, y, n_splits: int = 5,
                       num_boost_round: int = 1000, use_gpu: bool = False) -> dict:
        """
        Оценивает надёжность модели через StratifiedKFold CV.
        Не заменяет финальное обучение — только даёт честную оценку метрик.
        """
        params = self._build_params(use_gpu=use_gpu, gpu_available=False)
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

        fold_metrics: dict[str, list] = {
            k: [] for k in ('accuracy', 'precision', 'recall', 'f1', 'f2', 'auc')
        }

        print(f"\n{'='*58}")
        print(f"КРОСС-ВАЛИДАЦИЯ  ({n_splits} фолдов, StratifiedKFold)")
        print(f"{'='*58}")

        for fold_idx, (tr_idx, val_idx) in enumerate(skf.split(X, y), 1):
            X_tr, X_val_fold = X[tr_idx], X[val_idx]
            y_tr, y_val_fold = y[tr_idx], y[val_idx]

            # inner split для early stopping внутри фолда
            X_tr, X_es, y_tr, y_es = train_test_split(
                X_tr, y_tr, test_size=0.15, random_state=fold_idx, stratify=y_tr
            )

            X_tr        = np.ascontiguousarray(X_tr, dtype=np.float32)
            X_es        = np.ascontiguousarray(X_es, dtype=np.float32)
            X_val_fold  = np.ascontiguousarray(X_val_fold, dtype=np.float32)

            fold_params = dict(params)
            n_neg = int(np.sum(y_tr == 0))
            n_pos = int(np.sum(y_tr == 1))
            fold_params['scale_pos_weight'] = n_neg / n_pos if n_pos > 0 else 1.0

            tr_ds = lgb.Dataset(X_tr, label=y_tr)
            es_ds = lgb.Dataset(X_es, label=y_es, reference=tr_ds)

            fold_model = lgb.train(
                fold_params,
                tr_ds,
                num_boost_round=num_boost_round,
                valid_sets=[es_ds],
                valid_names=['es'],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=50, verbose=False),
                    lgb.log_evaluation(period=-1),
                ],
            )

            y_proba = fold_model.predict(X_val_fold)
            y_pred  = (y_proba >= 0.5).astype(int)

            acc  = accuracy_score(y_val_fold, y_pred)
            prec = precision_score(y_val_fold, y_pred, zero_division=0)
            rec  = recall_score(y_val_fold, y_pred, zero_division=0)
            f1   = f1_score(y_val_fold, y_pred, zero_division=0)
            f2   = fbeta_score(y_val_fold, y_pred, beta=2, zero_division=0)
            auc  = roc_auc_score(y_val_fold, y_proba)

            for key, val in zip(
                ('accuracy', 'precision', 'recall', 'f1', 'f2', 'auc'),
                (acc, prec, rec, f1, f2, auc)
            ):
                fold_metrics[key].append(val)

            best_iter = fold_model.best_iteration or num_boost_round
            print(f"  Фолд {fold_idx}/{n_splits}:  "
                  f"AUC={auc:.4f}  Recall={rec:.4f}  "
                  f"F2={f2:.4f}  (итераций: {best_iter})")

        print(f"\n  {'Метрика':<12} {'Среднее':>10} {'± Std':>10}")
        print(f"  {'-'*34}")
        for label, key in [
            ('Accuracy',  'accuracy'),
            ('Precision', 'precision'),
            ('Recall',    'recall'),
            ('F1-score',  'f1'),
            ('F2-score',  'f2'),
            ('ROC AUC',   'auc'),
        ]:
            vals = fold_metrics[key]
            print(f"  {label:<12} {np.mean(vals):>10.4f} {np.std(vals):>10.4f}")
        print(f"{'='*58}\n")

        return {k: (float(np.mean(v)), float(np.std(v))) for k, v in fold_metrics.items()}

    def find_optimal_threshold(self, X_val, y_val) -> float:
        """
        Подбирает порог классификации по F2-score на валидационной выборке.
        F2 весит recall в 2 раза больше precision — критично для антивируса.
        """
        X_val = np.ascontiguousarray(X_val, dtype=np.float32)
        y_proba = self.model.predict(X_val)

        auc = roc_auc_score(y_val, y_proba)
        print(f"\nROC AUC на валидации: {auc:.4f}")

        thresholds = np.arange(0.05, 0.95, 0.01)
        best_t, best_f2 = 0.5, 0.0
        for t in thresholds:
            y_pred = (y_proba >= t).astype(int)
            f2 = fbeta_score(y_val, y_pred, beta=2, zero_division=0)
            if f2 > best_f2:
                best_f2, best_t = f2, float(t)

        y_pred_05  = (y_proba >= 0.5).astype(int)
        y_pred_opt = (y_proba >= best_t).astype(int)

        print("\nСравнение порогов на валидации:")
        print(f"{'Метрика':<12} {'0.50 (было)':>14} {f'{best_t:.2f} (оптимум)':>16}")
        print("-" * 44)
        for name, fn in [
            ('Recall',    lambda y, p: recall_score(y, p, zero_division=0)),
            ('Precision', lambda y, p: precision_score(y, p, zero_division=0)),
            ('F2-score',  lambda y, p: fbeta_score(y, p, beta=2, zero_division=0)),
        ]:
            v05  = fn(y_val, y_pred_05)
            vopt = fn(y_val, y_pred_opt)
            print(f"{name:<12} {v05:>14.4f} {vopt:>16.4f}")
        print(f"\nОптимальный порог: {best_t:.2f} (F2={best_f2:.4f})")
        return best_t

    def save_threshold(self, threshold: float, path: str):
        """Сохраняет оптимальный порог в JSON рядом с моделью."""
        with open(path, 'w') as f:
            json.dump({'threshold': round(threshold, 4)}, f, indent=2)
        print(f"Порог сохранён: {path}")

    def evaluate(self, X_test, y_test, threshold: float = 0.5):
        """
        Оценивает модель на тестовой выборке.

        Returns:
            Словарь с метриками
        """
        if self.model is None:
            raise ValueError("Модель не обучена!")

        print(f"\nОценка модели на тестовой выборке (порог={threshold:.2f})...")

        y_pred_proba = self.model.predict(X_test)
        y_pred = (y_pred_proba >= threshold).astype(int)
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        print("\n" + "="*50)
        print("МЕТРИКИ МОДЕЛИ")
        print("="*50)
        print(f"Accuracy:  {accuracy:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall:    {recall:.4f}")
        print(f"F1-Score:  {f1:.4f}")
        print("="*50)
        
        print("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(cm)
        
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Легитимный', 'Малварь']))
        
        # Важность признаков
        if hasattr(self.model, 'feature_importance'):
            importances = self.model.feature_importance(importance_type='gain')
            if len(importances) == len(self.feature_names):
                feature_importance = list(zip(self.feature_names, importances))
                feature_importance.sort(key=lambda x: x[1], reverse=True)
                
                print("\nТоп-20 важных признаков:")
                for i, (name, importance) in enumerate(feature_importance[:20], 1):
                    print(f"{i:2d}. {name:40s} {importance:10.2f}")
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'confusion_matrix': cm.tolist()
        }
    
    def save_model(self, model_path: str, feature_names_path: str = None):
        """Сохраняет модель и список признаков."""
        if self.model is None:
            raise ValueError("Модель не обучена!")
        
        # Сохранение модели
        self.model.save_model(model_path)
        print(f"Модель сохранена: {model_path}")
        
        # Сохранение списка признаков
        if feature_names_path:
            with open(feature_names_path, 'w') as f:
                json.dump(self.feature_names, f, indent=2)
            print(f"Список признаков сохранен: {feature_names_path}")
    
    def load_model(self, model_path: str, feature_names_path: str = None):
        """Загружает модель и список признаков."""
        self.model = lgb.Booster(model_file=model_path)
        print(f"Модель загружена: {model_path}")
        
        if feature_names_path and os.path.exists(feature_names_path):
            with open(feature_names_path, 'r') as f:
                self.feature_names = json.load(f)
            print(f"Список признаков загружен: {feature_names_path}")


def main():
    parser = argparse.ArgumentParser(description='Обучение модели детекции малвари')
    parser.add_argument('--ember-dir', type=str, help='Путь к директории с датасетом EMBER')
    parser.add_argument('--malware-dir', type=str, help='Путь к директории с малварью')
    parser.add_argument('--benign-dir', type=str, help='Путь к директории с легитимными файлами')
    parser.add_argument('--max-samples', type=int, help='Максимальное количество образцов на класс')
    parser.add_argument('--model-output', type=str, default='model/malware_detector.model',
                       help='Путь для сохранения модели')
    parser.add_argument('--features-output', type=str, default='model/feature_names.json',
                       help='Путь для сохранения списка признаков')
    parser.add_argument('--threshold-output', type=str, default='model/threshold.json',
                       help='Путь для сохранения оптимального порога')
    parser.add_argument('--test-size', type=float, default=0.2, help='Доля тестовой выборки')
    parser.add_argument('--use-gpu', action='store_true',
                       help='Использовать GPU для обучения (если доступен)')
    parser.add_argument('--num-boost-round', type=int, default=1000,
                       help='Максимальное количество итераций бустинга')
    parser.add_argument('--cv-folds', type=int, default=5,
                       help='Количество фолдов кросс-валидации (0 — отключить)')
    parser.add_argument('--tune', action='store_true',
                       help='Запустить подбор гиперпараметров через Optuna')
    parser.add_argument('--tune-trials', type=int, default=50,
                       help='Количество триалов Optuna (по умолчанию: 50)')
    
    args = parser.parse_args()
    
    # Вывод информации о системе и видеокартах
    print_system_info()

    total_start = time.perf_counter()

    # Создание директории для модели
    os.makedirs(os.path.dirname(args.model_output), exist_ok=True)
    
    trainer = MalwareDetectorTrainer()
    
    # Загрузка данных
    if args.ember_dir:
        X_train, y_train, X_test, y_test = trainer.load_ember_dataset(args.ember_dir)
        if X_train is None:
            print("Не удалось загрузить EMBER. Используйте --malware-dir и --benign-dir")
            return
    else:
        if not args.malware_dir or not args.benign_dir:
            print("Укажите либо --ember-dir, либо --malware-dir и --benign-dir")
            return
        
        X, y = trainer.extract_features_from_directory(
            args.malware_dir, 
            args.benign_dir,
            max_samples_per_class=args.max_samples
        )
    
        # Разделение на train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, random_state=42, stratify=y
        )
    
    # Кросс-валидация на обучающей выборке (X_test не трогается)
    if args.cv_folds > 0:
        trainer.cross_validate(
            X_train, y_train,
            n_splits=args.cv_folds,
            num_boost_round=args.num_boost_round,
            use_gpu=args.use_gpu,
        )

    # Подбор гиперпараметров (опционально)
    best_params = None
    if args.tune:
        best_params = trainer.tune_hyperparams(
            X_train, y_train,
            n_trials=args.tune_trials,
            use_gpu=args.use_gpu,
        )

    # Разделение train на train/val для финального обучения с early stopping
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )

    # Финальное обучение
    trainer.train(X_train, y_train, X_val, y_val,
                  params=best_params,
                  use_gpu=args.use_gpu,
                  num_boost_round=args.num_boost_round)

    # Подбор оптимального порога на валидации
    optimal_threshold = trainer.find_optimal_threshold(X_val, y_val)

    # Оценка на тесте с оптимальным порогом
    metrics = trainer.evaluate(X_test, y_test, threshold=optimal_threshold)

    # Сохранение
    trainer.save_model(args.model_output, args.features_output)
    trainer.save_threshold(optimal_threshold, args.threshold_output)
    
    total_elapsed = time.perf_counter() - total_start
    print("\nОбучение завершено успешно!")
    print(f"Общее время выполнения: {format_duration(total_elapsed)}")


if __name__ == '__main__':
    main()

