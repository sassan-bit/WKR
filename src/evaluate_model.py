"""
Скрипт для оценки модели на тестовой выборке и сравнения с ClamAV.
"""

import os
import sys
import subprocess
import json
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
import lightgbm as lgb
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))
from feature_extractor import PEFeatureExtractor
from check_file import MalwareDetector
import argparse
from tqdm import tqdm


def evaluate_on_directory(detector: MalwareDetector, directory: str, 
                         true_label: int, threshold: float = 0.5):
    """
    Оценивает модель на файлах в директории.
    
    Args:
        detector: Объект детектора
        directory: Путь к директории с файлами
        true_label: Истинная метка (0 - легитимный, 1 - малварь)
        threshold: Порог вероятности
        
    Returns:
        Словарь с результатами
    """
    if not os.path.exists(directory):
        return None
    
    files = [f for f in os.listdir(directory) 
             if f.lower().endswith(('.exe', '.dll', '.sys'))]
    
    if not files:
        return None
    
    results = []
    for filename in tqdm(files, desc=f"Обработка {os.path.basename(directory)}"):
        file_path = os.path.join(directory, filename)
        result = detector.check_file(file_path, threshold)
        
        if 'error' not in result:
            results.append({
                'file': filename,
                'true_label': true_label,
                'predicted_label': 1 if result['is_malware'] else 0,
                'probability': result['probability']
            })
    
    return results


def compare_with_clamav(test_dir: str, malware_dir: str = None, 
                        benign_dir: str = None, max_files: int = 200):
    """
    Сравнивает модель с ClamAV на тестовой выборке.
    
    Args:
        test_dir: Директория с тестовыми файлами
        malware_dir: Директория с малварью (если файлы не размечены)
        benign_dir: Директория с легитимными файлами (если файлы не размечены)
        max_files: Максимальное количество файлов для проверки
    """
    print("Проверка наличия ClamAV...")
    
    # Проверка ClamAV
    try:
        result = subprocess.run(['clamscan', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("⚠️  ClamAV не найден или не установлен.")
            print("Установите ClamAV для сравнения:")
            print("  Windows: https://www.clamav.net/downloads")
            print("  Linux: sudo apt-get install clamav")
            return
        print(f"ClamAV найден: {result.stdout.strip()}")
    except FileNotFoundError:
        print("⚠️  ClamAV не найден. Пропускаем сравнение с ClamAV.")
        return
    except Exception as e:
        print(f"⚠️  Ошибка при проверке ClamAV: {e}")
        return
    
    print("\nСравнение с ClamAV...")
    
    # Сбор файлов
    all_files = []
    
    if malware_dir and os.path.exists(malware_dir):
        malware_files = [os.path.join(malware_dir, f) 
                        for f in os.listdir(malware_dir)
                        if f.lower().endswith(('.exe', '.dll', '.sys'))]
        all_files.extend([(f, 1) for f in malware_files[:max_files//2]])
    
    if benign_dir and os.path.exists(benign_dir):
        benign_files = [os.path.join(benign_dir, f) 
                       for f in os.listdir(benign_dir)
                       if f.lower().endswith(('.exe', '.dll', '.sys'))]
        all_files.extend([(f, 0) for f in benign_files[:max_files//2]])
    
    if not all_files:
        print("Не найдено файлов для сравнения.")
        return
    
    results = []
    
    for file_path, true_label in tqdm(all_files[:max_files], desc="Сравнение"):
        # Проверка нашей модели
        # (нужно загрузить детектор отдельно)
        
        # Проверка ClamAV
        try:
            result = subprocess.run(['clamscan', '--no-summary', file_path],
                                  capture_output=True, text=True, timeout=10)
            clamav_detected = result.returncode == 1  # ClamAV возвращает 1 при обнаружении
        except:
            clamav_detected = False
        
        results.append({
            'file': os.path.basename(file_path),
            'true_label': true_label,
            'clamav_detected': clamav_detected
        })
    
    # Подсчет метрик ClamAV
    y_true = [r['true_label'] for r in results]
    y_clamav = [1 if r['clamav_detected'] else 0 for r in results]
    
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ СРАВНЕНИЯ С ClamAV")
    print("="*60)
    
    accuracy = accuracy_score(y_true, y_clamav)
    precision = precision_score(y_true, y_clamav, zero_division=0)
    recall = recall_score(y_true, y_clamav, zero_division=0)
    f1 = f1_score(y_true, y_clamav, zero_division=0)
    
    print(f"\nClamAV:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1-Score:  {f1:.4f}")
    
    print("\nConfusion Matrix (ClamAV):")
    print(confusion_matrix(y_true, y_clamav))
    
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Оценка модели на тестовой выборке')
    parser.add_argument('--model', type=str, default='model/malware_detector.model',
                       help='Путь к обученной модели')
    parser.add_argument('--features', type=str, default='model/feature_names.json',
                       help='Путь к файлу со списком признаков')
    parser.add_argument('--malware-dir', type=str, required=True,
                       help='Директория с тестовыми малварными файлами')
    parser.add_argument('--benign-dir', type=str, required=True,
                       help='Директория с тестовыми легитимными файлами')
    parser.add_argument('--threshold', type=float, default=0.5,
                       help='Порог вероятности для классификации')
    parser.add_argument('--compare-clamav', action='store_true',
                       help='Сравнить с ClamAV')
    parser.add_argument('--max-files', type=int, default=200,
                       help='Максимальное количество файлов для проверки')
    parser.add_argument('--output', type=str,
                       help='Путь для сохранения результатов в JSON')
    
    args = parser.parse_args()
    
    # Загрузка детектора
    if not os.path.exists(args.model) or not os.path.exists(args.features):
        print("ОШИБКА: Модель или файл признаков не найдены!")
        print("Сначала обучите модель с помощью train_model.py")
        sys.exit(1)
    
    detector = MalwareDetector(args.model, args.features)
    
    # Оценка на тестовых данных
    print("Оценка модели на тестовой выборке...\n")
    
    malware_results = evaluate_on_directory(
        detector, args.malware_dir, true_label=1, threshold=args.threshold
    )
    benign_results = evaluate_on_directory(
        detector, args.benign_dir, true_label=0, threshold=args.threshold
    )
    
    if not malware_results or not benign_results:
        print("ОШИБКА: Не удалось обработать файлы из тестовых директорий!")
        sys.exit(1)
    
    # Объединение результатов
    all_results = malware_results + benign_results
    
    y_true = [r['true_label'] for r in all_results]
    y_pred = [r['predicted_label'] for r in all_results]
    
    # Вычисление метрик
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ОЦЕНКИ МОДЕЛИ")
    print("="*60)
    print(f"Тестовых образцов: {len(all_results)}")
    print(f"  Малварь: {len(malware_results)}")
    print(f"  Легитимные: {len(benign_results)}")
    print()
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print("="*60)
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_true, y_pred)
    print(cm)
    
    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, target_names=['Легитимный', 'Малварь']))
    
    # Сохранение результатов
    if args.output:
        results_dict = {
            'metrics': {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1': float(f1)
            },
            'confusion_matrix': cm.tolist(),
            'results': all_results
        }
        
        with open(args.output, 'w') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        print(f"\nРезультаты сохранены: {args.output}")
    
    # Сравнение с ClamAV
    if args.compare_clamav:
        print("\n")
        compare_with_clamav(
            test_dir=None,
            malware_dir=args.malware_dir,
            benign_dir=args.benign_dir,
            max_files=args.max_files
        )


if __name__ == '__main__':
    main()

