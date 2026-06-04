"""
Скрипт для проверки всех файлов в указанной директории на наличие малвари.
Использование: python check_folder.py [путь_к_папке]
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))
from check_file import MalwareDetector
from tqdm import tqdm

# Цветной вывод
try:
    from colorama import init, Fore, Style, Back
    # Инициализация colorama для Windows
    init(autoreset=True, strip=False)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Заглушки для случая, когда colorama не установлен
    class Fore:
        RED = ''
        GREEN = ''
        YELLOW = ''
        RESET = ''
    class Style:
        BRIGHT = ''
        RESET_ALL = ''
    class Back:
        RED = ''
        RESET = ''


def check_folder(folder_path: str, model_path: str = 'model/malware_detector.model',
                 features_path: str = 'model/feature_names.json', threshold: float = 0.5,
                 output_file: str = None, move_detected: bool = False, 
                 detected_folder: str = None):
    """
    Проверяет все PE-файлы в указанной директории.
    
    Args:
        folder_path: Путь к директории с файлами для проверки
        model_path: Путь к модели
        features_path: Путь к файлу признаков
        threshold: Порог вероятности
        output_file: Путь для сохранения результатов в JSON (опционально)
        move_detected: Перемещать обнаруженные файлы в отдельную папку
        detected_folder: Папка для перемещения обнаруженных файлов
    """
    if not os.path.exists(folder_path):
        print(f"ОШИБКА: Директория не найдена: {folder_path}")
        sys.exit(1)
    
    if not os.path.exists(model_path) or not os.path.exists(features_path):
        print(f"ОШИБКА: Модель не найдена!")
        print("Сначала обучите модель с помощью train_model.py")
        sys.exit(1)
    
    # Загрузка детектора
    try:
        detector = MalwareDetector(model_path, features_path)
    except Exception as e:
        print(f"ОШИБКА при загрузке модели: {e}")
        sys.exit(1)
    
    # Поиск PE-файлов
    pe_extensions = ('.exe', '.dll', '.sys', '.scr', '.com')
    files = []
    
    for ext in pe_extensions:
        # Ищем файлы с расширениями в разных регистрах
        files.extend(Path(folder_path).glob(f'*{ext}'))
        files.extend(Path(folder_path).glob(f'*{ext.upper()}'))
    
    # Убираем дубликаты (на Windows регистр не важен для имен файлов)
    files = list(set(files))
    
    if not files:
        print(f"В директории {folder_path} не найдено PE-файлов для проверки.")
        print("Поддерживаемые расширения: .exe, .dll, .sys, .scr, .com")
        return
    
    print("\n" + "=" * 70)
    print("ПРОВЕРКА ФАЙЛОВ НА МАЛВАРЬ")
    print("=" * 70)
    print(f"Директория: {folder_path}")
    print(f"Найдено файлов: {len(files)}")
    print(f"Порог вероятности: {threshold}")
    print("=" * 70 + "\n")
    
    # Создание папки для обнаруженных файлов (если нужно)
    if move_detected:
        if detected_folder is None:
            detected_folder = os.path.join(folder_path, "detected_malware")
        os.makedirs(detected_folder, exist_ok=True)
        print(f"Обнаруженные файлы будут перемещены в: {detected_folder}\n")
    
    # Проверка файлов
    results = []
    detected_count = 0
    clean_count = 0
    error_count = 0
    
    # Используем tqdm с отключенным выводом для чистоты цветного вывода
    for file_path in tqdm(files, desc="Проверка файлов", disable=False):
        result = detector.check_file(str(file_path), threshold)
        
        if 'error' in result:
            error_count += 1
            results.append({
                'file': os.path.basename(str(file_path)),
                'path': str(file_path),
                'status': 'error',
                'error': result['error']
            })
            continue
        
        is_malware = result['is_malware']
        probability = result['probability']
        
        if is_malware:
            detected_count += 1
            status = 'MALWARE'
        else:
            clean_count += 1
            status = 'CLEAN'
        
        results.append({
            'file': os.path.basename(str(file_path)),
            'path': str(file_path),
            'status': status,
            'is_malware': is_malware,
            'probability': probability,
            'verdict': result['verdict']
        })
        
        # Перемещение обнаруженных файлов
        if move_detected and is_malware:
            try:
                dest_path = os.path.join(detected_folder, os.path.basename(str(file_path)))
                # Если файл с таким именем уже существует, добавляем номер
                counter = 1
                base_name, ext = os.path.splitext(dest_path)
                while os.path.exists(dest_path):
                    dest_path = f"{base_name}_{counter}{ext}"
                    counter += 1
                
                os.rename(str(file_path), dest_path)
                results[-1]['moved_to'] = dest_path
            except Exception as e:
                results[-1]['move_error'] = str(e)
    
    # Разделение результатов на группы
    malware_results = [r for r in results if r['status'] == 'MALWARE']
    clean_results = [r for r in results if r['status'] == 'CLEAN']
    error_results = [r for r in results if r['status'] == 'error']
    
    # Сортировка по вероятности (малварь - по убыванию, легитимные - по возрастанию)
    malware_results.sort(key=lambda x: x['probability'], reverse=True)
    clean_results.sort(key=lambda x: x['probability'])
    
    # Вывод результатов
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    print("=" * 70)
    print(f"Всего проверено: {len(files)}")
    if COLORAMA_AVAILABLE:
        print(f"  {Fore.GREEN}[OK]{Fore.RESET} Легитимные: {clean_count}")
        print(f"  {Fore.RED}{Style.BRIGHT}[WARNING]{Style.RESET_ALL} {Fore.RED}Малварь: {detected_count}{Fore.RESET}")
        if error_count > 0:
            print(f"  {Fore.YELLOW}[ERROR]{Fore.RESET} Ошибки: {error_count}")
    else:
        print(f"  [OK] Легитимные: {clean_count}")
        print(f"  [WARNING] Малварь: {detected_count}")
        if error_count > 0:
            print(f"  [ERROR] Ошибки: {error_count}")
    print("=" * 70)
    
    # Группированный вывод: сначала малварь (красным), потом легитимные (зеленым)
    
    # 1. МАЛВАРЬ (заголовок обычным, файлы красным)
    if malware_results:
        print(f"\n{'='*70}")
        print(f"ОБНАРУЖЕНА МАЛВАРЬ ({len(malware_results)} файлов):")
        print(f"{'='*70}")
        
        for result in malware_results:
            prob_percent = result['probability'] * 100
            if COLORAMA_AVAILABLE:
                print(f"{Fore.RED}{Style.BRIGHT}[MALWARE]{Style.RESET_ALL} {Fore.RED}{result['file']:50s} "
                      f"МАЛВАРЬ ({prob_percent:.2f}%){Fore.RESET}")
            else:
                print(f"[MALWARE] {result['file']:50s} МАЛВАРЬ ({prob_percent:.2f}%)")
            
            if 'moved_to' in result:
                if COLORAMA_AVAILABLE:
                    print(f"    {Fore.YELLOW}-> Перемещен в: {result['moved_to']}{Fore.RESET}")
                else:
                    print(f"    -> Перемещен в: {result['moved_to']}")
    
    # 2. ЛЕГИТИМНЫЕ (заголовок обычным, файлы зеленым)
    if clean_results:
        print(f"\n{'='*70}")
        print(f"ЛЕГИТИМНЫЕ ФАЙЛЫ ({len(clean_results)} файлов):")
        print(f"{'='*70}")
        
        for result in clean_results:
            prob_percent = result['probability'] * 100
            if COLORAMA_AVAILABLE:
                print(f"{Fore.GREEN}[OK]{Fore.RESET} {result['file']:50s} "
                      f"Легитимный ({prob_percent:.2f}%)")
            else:
                print(f"[OK] {result['file']:50s} Легитимный ({prob_percent:.2f}%)")
    
    # 3. ОШИБКИ (желтым цветом)
    if error_results:
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.YELLOW}{'='*70}")
            print(f"ОШИБКИ ПРИ ОБРАБОТКЕ ({len(error_results)} файлов):")
            print(f"{'='*70}{Fore.RESET}")
        else:
            print(f"\n{'='*70}")
            print(f"ОШИБКИ ПРИ ОБРАБОТКЕ ({len(error_results)} файлов):")
            print(f"{'='*70}")
        
        for result in error_results:
            if COLORAMA_AVAILABLE:
                print(f"{Fore.YELLOW}[ERROR]{Fore.RESET} {result['file']:50s} "
                      f"ОШИБКА: {result.get('error', 'Неизвестная ошибка')}")
            else:
                print(f"[ERROR] {result['file']:50s} ОШИБКА: {result.get('error', 'Неизвестная ошибка')}")
    
    print("-" * 70)
    
    # Сохранение результатов
    if output_file:
        output_data = {
            'summary': {
                'total': len(files),
                'clean': clean_count,
                'malware': detected_count,
                'errors': error_count
            },
            'results': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nРезультаты сохранены в: {output_file}")
    
    # Итоговый вердикт
    print("\n" + "=" * 70)
    if detected_count > 0:
        if COLORAMA_AVAILABLE:
            print(f"{Fore.RED}{Style.BRIGHT}[WARNING] ВНИМАНИЕ: Обнаружено {detected_count} подозрительных файлов!{Style.RESET_ALL}{Fore.RESET}")
        else:
            print(f"[WARNING] ВНИМАНИЕ: Обнаружено {detected_count} подозрительных файлов!")
    else:
        if COLORAMA_AVAILABLE:
            print(f"{Fore.GREEN}[OK] Все файлы определены как легитимные{Fore.RESET}")
        else:
            print("[OK] Все файлы определены как легитимные")
    print("=" * 70 + "\n")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Проверка всех PE-файлов в директории на малварь',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python check_folder.py files_to_check
  python check_folder.py files_to_check --threshold 0.7
  python check_folder.py files_to_check --output results.json
  python check_folder.py files_to_check --move-detected
        """
    )
    
    parser.add_argument('folder', type=str, nargs='?', default='files_to_check',
                       help='Директория с файлами для проверки (по умолчанию: files_to_check)')
    parser.add_argument('--model', type=str, default='model/malware_detector.model',
                       help='Путь к модели')
    parser.add_argument('--features', type=str, default='model/feature_names.json',
                       help='Путь к файлу признаков')
    parser.add_argument('--threshold', type=float, default=0.5,
                       help='Порог вероятности (по умолчанию: 0.5)')
    parser.add_argument('--output', type=str,
                       help='Путь для сохранения результатов в JSON')
    parser.add_argument('--move-detected', action='store_true',
                       help='Перемещать обнаруженные файлы в отдельную папку')
    parser.add_argument('--detected-folder', type=str,
                       help='Папка для перемещения обнаруженных файлов (по умолчанию: folder/detected_malware)')
    
    args = parser.parse_args()
    
    check_folder(
        args.folder,
        args.model,
        args.features,
        args.threshold,
        args.output,
        args.move_detected,
        args.detected_folder
    )


if __name__ == '__main__':
    main()

