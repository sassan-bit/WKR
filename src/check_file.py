"""
Консольный скрипт для проверки PE-файлов на наличие малвари.
Использование: python check_file.py suspicious.exe
"""

import os
import sys
import json
import numpy as np
import lightgbm as lgb
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))
from feature_extractor import PEFeatureExtractor
import argparse


class MalwareDetector:
    """Класс для детекции малвари в PE-файлах."""
    
    def __init__(self, model_path: str, feature_names_path: str):
        self.model = lgb.Booster(model_file=model_path)
        self.feature_extractor = PEFeatureExtractor()

        with open(feature_names_path, 'r') as f:
            self.feature_names = json.load(f)

        threshold_path = Path(model_path).parent / 'threshold.json'
        if threshold_path.exists():
            with open(threshold_path) as f:
                self.threshold = json.load(f).get('threshold', 0.5)
        else:
            self.threshold = 0.5

        print(f"Модель загружена: {model_path}")
        print(f"Количество признаков: {len(self.feature_names)}")
        print(f"Порог детекции: {self.threshold:.2f}")
    
    def check_file(self, file_path: str, threshold: float = None) -> dict:
        """
        Проверяет файл на наличие малвари.

        Args:
            file_path: Путь к проверяемому файлу
            threshold: Порог вероятности. Если None — используется оптимальный из threshold.json

        Returns:
            Словарь с результатами проверки
        """
        if threshold is None:
            threshold = self.threshold
        if not os.path.exists(file_path):
            return {
                'error': f'Файл не найден: {file_path}',
                'is_malware': False,
                'probability': 0.0
            }
        
        # Извлечение признаков
        features = self.feature_extractor.extract_features(file_path)
        
        if features is None:
            return {
                'error': 'Не удалось извлечь признаки. Файл может быть поврежден или не является валидным PE.',
                'is_malware': False,
                'probability': 0.0
            }
        
        # Преобразование в вектор
        feature_vector = self.feature_extractor.get_feature_vector(features, self.feature_names)
        
        # Предсказание
        probability = float(self.model.predict(feature_vector.reshape(1, -1))[0])
        is_malware = probability >= threshold
        
        return {
            'file_path': file_path,
            'is_malware': bool(is_malware),
            'probability': probability,
            'threshold': threshold,
            'verdict': 'МАЛВАРЬ' if is_malware else 'ЛЕГИТИМНЫЙ'
        }


def main():
    parser = argparse.ArgumentParser(
        description='Проверка PE-файла на наличие малвари',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python check_file.py suspicious.exe
  python check_file.py suspicious.exe --threshold 0.7
  python check_file.py suspicious.exe --model model/malware_detector.model
        """
    )
    
    parser.add_argument('file_path', type=str, help='Путь к проверяемому PE-файлу')
    parser.add_argument('--model', type=str, default='model/malware_detector.model',
                       help='Путь к обученной модели (по умолчанию: model/malware_detector.model)')
    parser.add_argument('--features', type=str, default='model/feature_names.json',
                       help='Путь к файлу со списком признаков (по умолчанию: model/feature_names.json)')
    parser.add_argument('--threshold', type=float, default=None,
                       help='Порог вероятности (по умолчанию: из model/threshold.json или 0.5)')
    parser.add_argument('--json', action='store_true',
                       help='Вывести результат в формате JSON')
    
    args = parser.parse_args()
    
    # Проверка существования файлов модели
    if not os.path.exists(args.model):
        print(f"ОШИБКА: Модель не найдена: {args.model}")
        print("Сначала обучите модель с помощью train_model.py")
        sys.exit(1)
    
    if not os.path.exists(args.features):
        print(f"ОШИБКА: Файл с признаками не найден: {args.features}")
        print("Сначала обучите модель с помощью train_model.py")
        sys.exit(1)
    
    # Инициализация детектора
    try:
        detector = MalwareDetector(args.model, args.features)
    except Exception as e:
        print(f"ОШИБКА при загрузке модели: {e}")
        sys.exit(1)
    
    # Проверка файла
    result = detector.check_file(args.file_path, args.threshold)
    
    # Вывод результата
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТ ПРОВЕРКИ")
        print("="*60)
        
        if 'error' in result:
            print(f"ОШИБКА: {result['error']}")
        else:
            print(f"Файл:        {result['file_path']}")
            print(f"Вердикт:     {result['verdict']}")
            print(f"Вероятность: {result['probability']:.4f} ({result['probability']*100:.2f}%)")
            print(f"Порог:       {result['threshold']:.2f}")
            
            if result['is_malware']:
                print("\n⚠️  ВНИМАНИЕ: Файл определен как МАЛВАРЬ!")
            else:
                print("\n✓ Файл определен как ЛЕГИТИМНЫЙ")
        
        print("="*60 + "\n")
    
    # Код возврата для скриптов
    if result.get('is_malware', False):
        sys.exit(1)  # Малварь обнаружена
    elif 'error' in result:
        sys.exit(2)  # Ошибка
    else:
        sys.exit(0)  # Легитимный файл


if __name__ == '__main__':
    main()

