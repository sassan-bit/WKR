"""
Скрипт для сбора легитимных Windows PE-файлов для тестирования.
Копирует безопасные системные файлы и файлы из установленных программ.
"""

import os
import shutil
import argparse
from pathlib import Path


def collect_system_files(output_dir: str, max_files: int = 100):
    """
    Собирает легитимные PE-файлы из системных директорий Windows.
    
    Args:
        output_dir: Директория для сохранения файлов
        max_files: Максимальное количество файлов для копирования
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Безопасные системные директории Windows
    system_dirs = [
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
        r"C:\Windows\System32\drivers",
    ]
    
    # Безопасные имена файлов (известные системные утилиты)
    safe_files = [
        "notepad.exe",
        "calc.exe",
        "mspaint.exe",
        "cmd.exe",
        "explorer.exe",
        "regedit.exe",
        "taskmgr.exe",
        "winver.exe",
        "write.exe",
        "charmap.exe",
        "osk.exe",
        "snippingtool.exe",
        "mstsc.exe",
        "dxdiag.exe",
        "msinfo32.exe",
    ]
    
    # Расширения PE-файлов
    pe_extensions = ('.exe', '.dll', '.sys')
    
    collected = 0
    skipped = 0
    
    print("Сбор легитимных PE-файлов из системных директорий...")
    print("=" * 60)
    
    # Сначала копируем известные безопасные файлы
    for sys_dir in system_dirs:
        if not os.path.exists(sys_dir):
            continue
        
        for safe_file in safe_files:
            if collected >= max_files:
                break
            
            source_path = os.path.join(sys_dir, safe_file)
            if os.path.exists(source_path):
                try:
                    dest_path = output_path / safe_file
                    if not dest_path.exists():
                        shutil.copy2(source_path, dest_path)
                        print(f"[OK] Скопирован: {safe_file}")
                        collected += 1
                    else:
                        skipped += 1
                except PermissionError:
                    print(f"[SKIP] Пропущен (нет прав): {safe_file}")
                    skipped += 1
                except Exception as e:
                    print(f"[ERROR] Ошибка при копировании {safe_file}: {e}")
                    skipped += 1
    
    # Затем собираем другие DLL из System32
    if collected < max_files and os.path.exists(r"C:\Windows\System32"):
        print("\nСбор дополнительных DLL из System32...")
        system32_path = Path(r"C:\Windows\System32")
        
        for dll_file in system32_path.glob("*.dll"):
            if collected >= max_files:
                break
            
            # Пропускаем слишком большие файлы и известные проблемные
            if dll_file.stat().st_size > 50 * 1024 * 1024:  # > 50 MB
                continue
            
            # Пропускаем файлы с подозрительными именами
            skip_patterns = ['api-', 'ext-', 'winrt-', 'msvcp', 'vcruntime']
            if any(pattern in dll_file.name.lower() for pattern in skip_patterns):
                continue
            
            try:
                dest_path = output_path / dll_file.name
                if not dest_path.exists():
                    shutil.copy2(dll_file, dest_path)
                    print(f"✓ Скопирован: {dll_file.name}")
                    collected += 1
                else:
                    skipped += 1
            except PermissionError:
                skipped += 1
            except Exception as e:
                skipped += 1
    
    print("\n" + "=" * 60)
    print(f"Собрано файлов: {collected}")
    print(f"Пропущено: {skipped}")
    print(f"Директория: {output_dir}")
    print("=" * 60)
    
    return collected


def collect_from_installed_programs(output_dir: str, max_files: int = 50):
    """
    Собирает файлы из установленных программ.
    
    Args:
        output_dir: Директория для сохранения файлов
        max_files: Максимальное количество файлов
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Директории установленных программ
    program_dirs = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
    ]
    
    pe_extensions = ('.exe', '.dll')
    collected = 0
    
    print("\nСбор файлов из установленных программ...")
    print("=" * 60)
    
    for prog_dir in program_dirs:
        if not os.path.exists(prog_dir):
            continue
        
        for root, dirs, files in os.walk(prog_dir):
            if collected >= max_files:
                break
            
            # Пропускаем некоторые директории
            dirs[:] = [d for d in dirs if d not in ['Temp', 'temp', 'Cache', 'cache']]
            
            for file in files:
                if collected >= max_files:
                    break
                
                if file.lower().endswith(pe_extensions):
                    source_path = os.path.join(root, file)
                    
                    # Пропускаем слишком большие файлы
                    try:
                        if os.path.getsize(source_path) > 50 * 1024 * 1024:  # > 50 MB
                            continue
                    except:
                        continue
                    
                    # Создаем уникальное имя
                    dest_name = f"{Path(root).name}_{file}"
                    dest_path = output_path / dest_name
                    
                    if not dest_path.exists():
                        try:
                            shutil.copy2(source_path, dest_path)
                            print(f"[OK] Скопирован: {dest_name}")
                            collected += 1
                        except (PermissionError, OSError):
                            pass
    
    print(f"\nСобрано файлов из программ: {collected}")
    return collected


def main():
    parser = argparse.ArgumentParser(
        description='Сбор легитимных PE-файлов для тестирования',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python collect_benign_samples.py --output data/benign --max-files 200
  python collect_benign_samples.py --output data/benign --system-only
  python collect_benign_samples.py --output data/benign --programs-only --max-files 50
        """
    )
    
    parser.add_argument('--output', type=str, default='data/benign',
                       help='Директория для сохранения файлов (по умолчанию: data/benign)')
    parser.add_argument('--max-files', type=int, default=100,
                       help='Максимальное количество файлов для сбора (по умолчанию: 100)')
    parser.add_argument('--system-only', action='store_true',
                       help='Собирать только системные файлы')
    parser.add_argument('--programs-only', action='store_true',
                       help='Собирать только файлы из установленных программ')
    
    args = parser.parse_args()
    
    print("СБОР ЛЕГИТИМНЫХ PE-ФАЙЛОВ ДЛЯ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"Выходная директория: {args.output}")
    print(f"Максимум файлов: {args.max_files}")
    print("=" * 60)
    
    total_collected = 0
    
    # Сбор системных файлов
    if not args.programs_only:
        collected = collect_system_files(args.output, args.max_files)
        total_collected += collected
    
    # Сбор файлов из программ
    if not args.system_only and total_collected < args.max_files:
        remaining = args.max_files - total_collected
        collected = collect_from_installed_programs(args.output, remaining)
        total_collected += collected
    
    print("\n" + "=" * 60)
    print(f"ИТОГО СОБРАНО: {total_collected} файлов")
    print(f"Директория: {args.output}")
    print("=" * 60)
    
    if total_collected == 0:
        print("\n[WARNING] Не удалось собрать файлы. Возможные причины:")
        print("  - Нет прав доступа к системным директориям")
        print("  - Запустите скрипт от имени администратора")
        print("  - Или вручную скопируйте файлы в директорию")
    else:
        print("\n[SUCCESS] Файлы готовы для обучения модели!")
        print(f"  Используйте: python train_model.py --benign-dir {args.output}")


if __name__ == '__main__':
    main()

