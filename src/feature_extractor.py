"""
Модуль для извлечения статических признаков из PE-файлов.
Использует библиотеку pefile для анализа структуры PE-файлов.
"""

import pefile
import os
import numpy as np
from typing import Dict, Optional, List


class PEFeatureExtractor:
    """Класс для извлечения признаков из PE-файлов."""
    
    def __init__(self):
        self.feature_names = []
    
    def extract_features(self, file_path: str) -> Optional[Dict]:
        """
        Извлекает статические признаки из PE-файла.
        
        Args:
            file_path: Путь к PE-файлу
            
        Returns:
            Словарь с признаками или None, если файл не является валидным PE
        """
        MAX_BYTES = 5 * 1024 * 1024  # 5 МБ — достаточно для всех PE-признаков

        try:
            with open(file_path, 'rb') as f:
                data = f.read(MAX_BYTES)

            pe = pefile.PE(data=data)
            features = {}

            features.update(self._extract_file_features(file_path, data))
            features.update(self._extract_header_features(pe))
            features.update(self._extract_section_features(pe))
            features.update(self._extract_import_features(pe))
            features.update(self._extract_export_features(pe))
            features.update(self._extract_resource_features(pe))
            features.update(self._extract_string_features(data))

            pe.close()
            return features
            
        except pefile.PEFormatError:
            return None
        except Exception as e:
            print(f"Ошибка при обработке файла {file_path}: {e}")
            return None
    
    def _extract_file_features(self, file_path: str, data: bytes) -> Dict:
        """Извлекает базовые признаки файла."""
        features = {}

        try:
            file_size = os.path.getsize(file_path)  # реальный размер, не обрезанный
            features['file_size'] = file_size
            features['file_size_log'] = np.log1p(file_size)

            # Энтропия всего файла — ключевой признак упаковщиков (UPX, MPRESS и т.п.)
            file_entropy = self._calculate_entropy(data)
            features['file_entropy'] = file_entropy
            features['file_is_packed']    = file_entropy > 7.0  # упакован/зашифрован
            features['file_is_encrypted'] = file_entropy > 6.5  # сжат или обфусцирован

            # Энтропия первых/последних 512 байт
            features['file_entropy_first512'] = self._calculate_entropy(data[:512])
            features['file_entropy_last512']  = self._calculate_entropy(data[-512:])

        except Exception as e:
            print(f"Ошибка при извлечении файловых признаков: {e}")

        return features
    
    def _extract_header_features(self, pe: pefile.PE) -> Dict:
        """Извлекает признаки из заголовков PE."""
        features = {}
        
        try:
            # DOS Header
            features['e_magic'] = pe.DOS_HEADER.e_magic
            features['e_lfanew'] = pe.DOS_HEADER.e_lfanew
            
            # File Header
            if hasattr(pe, 'FILE_HEADER'):
                features['machine'] = pe.FILE_HEADER.Machine
                features['number_of_sections'] = pe.FILE_HEADER.NumberOfSections
                features['time_date_stamp'] = pe.FILE_HEADER.TimeDateStamp
                features['pointer_to_symbol_table'] = pe.FILE_HEADER.PointerToSymbolTable
                features['number_of_symbols'] = pe.FILE_HEADER.NumberOfSymbols
                features['size_of_optional_header'] = pe.FILE_HEADER.SizeOfOptionalHeader
                features['characteristics'] = pe.FILE_HEADER.Characteristics
            
            # Optional Header
            if hasattr(pe, 'OPTIONAL_HEADER'):
                opt_header = pe.OPTIONAL_HEADER
                features['magic'] = opt_header.Magic
                features['major_linker_version'] = opt_header.MajorLinkerVersion
                features['minor_linker_version'] = opt_header.MinorLinkerVersion
                features['size_of_code'] = opt_header.SizeOfCode
                features['size_of_initialized_data'] = opt_header.SizeOfInitializedData
                features['size_of_uninitialized_data'] = opt_header.SizeOfUninitializedData
                features['address_of_entry_point'] = opt_header.AddressOfEntryPoint
                features['base_of_code'] = opt_header.BaseOfCode
                features['image_base'] = opt_header.ImageBase
                features['section_alignment'] = opt_header.SectionAlignment
                features['file_alignment'] = opt_header.FileAlignment
                features['major_operating_system_version'] = opt_header.MajorOperatingSystemVersion
                features['minor_operating_system_version'] = opt_header.MinorOperatingSystemVersion
                features['major_image_version'] = opt_header.MajorImageVersion
                features['minor_image_version'] = opt_header.MinorImageVersion
                features['major_subsystem_version'] = opt_header.MajorSubsystemVersion
                features['minor_subsystem_version'] = opt_header.MinorSubsystemVersion
                features['size_of_image'] = opt_header.SizeOfImage
                features['size_of_headers'] = opt_header.SizeOfHeaders
                features['check_sum'] = opt_header.CheckSum
                features['subsystem'] = opt_header.Subsystem
                features['dll_characteristics'] = opt_header.DllCharacteristics
                features['size_of_stack_reserve'] = opt_header.SizeOfStackReserve
                features['size_of_stack_commit'] = opt_header.SizeOfStackCommit
                features['size_of_heap_reserve'] = opt_header.SizeOfHeapReserve
                features['size_of_heap_commit'] = opt_header.SizeOfHeapCommit
                features['loader_flags'] = opt_header.LoaderFlags
                features['number_of_rva_and_sizes'] = opt_header.NumberOfRvaAndSizes
                
                # Data Directories
                if hasattr(opt_header, 'DATA_DIRECTORY'):
                    for i, entry in enumerate(opt_header.DATA_DIRECTORY):
                        if entry:
                            features[f'data_directory_{i}_size'] = entry.Size
                            features[f'data_directory_{i}_virtual_address'] = entry.VirtualAddress
        
        except Exception as e:
            print(f"Ошибка при извлечении признаков заголовков: {e}")
        
        return features
    
    def _extract_section_features(self, pe: pefile.PE) -> Dict:
        """Извлекает признаки секций."""
        features = {}
        
        try:
            if not hasattr(pe, 'sections') or not pe.sections:
                return features
            
            sections = pe.sections
            features['num_sections'] = len(sections)
            
            # Статистики по секциям
            section_sizes = []
            section_entropies = []
            section_virtual_sizes = []
            section_names = []
            
            for section in sections:
                section_sizes.append(section.SizeOfRawData)
                section_virtual_sizes.append(section.Misc_VirtualSize)
                section_names.append(section.Name.decode('utf-8', errors='ignore').strip('\x00'))
                
                # Энтропия секции
                try:
                    data = section.get_data()
                    if len(data) > 0:
                        entropy = self._calculate_entropy(data)
                        section_entropies.append(entropy)
                except:
                    pass
            
            # Статистики
            if section_sizes:
                features['section_size_min'] = min(section_sizes)
                features['section_size_max'] = max(section_sizes)
                features['section_size_mean'] = np.mean(section_sizes)
                features['section_size_total'] = sum(section_sizes)
            
            if section_entropies:
                features['section_entropy_min'] = min(section_entropies)
                features['section_entropy_max'] = max(section_entropies)
                features['section_entropy_mean'] = np.mean(section_entropies)
            
            if section_virtual_sizes:
                features['section_virtual_size_min'] = min(section_virtual_sizes)
                features['section_virtual_size_max'] = max(section_virtual_sizes)
                features['section_virtual_size_mean'] = np.mean(section_virtual_sizes)
            
            # Признаки наличия специфичных секций
            section_names_lower = [name.lower() for name in section_names]
            features['has_text_section'] = any('text' in name or 'code' in name for name in section_names_lower)
            features['has_data_section'] = any('data' in name for name in section_names_lower)
            features['has_rsrc_section'] = any('rsrc' in name for name in section_names_lower)
            features['has_reloc_section'] = any('reloc' in name for name in section_names_lower)
            
        except Exception as e:
            print(f"Ошибка при извлечении признаков секций: {e}")
        
        return features
    
    def _extract_import_features(self, pe: pefile.PE) -> Dict:
        """Извлекает признаки импортов."""
        features = {}
        
        try:
            if not hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
                features['num_imports'] = 0
                features['num_imported_dlls'] = 0
                return features
            
            imports = []
            dlls = set()
            
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_name = entry.dll.decode('utf-8', errors='ignore').lower()
                dlls.add(dll_name)
                
                for imp in entry.imports:
                    if imp.name:
                        imports.append(imp.name.decode('utf-8', errors='ignore').lower())
            
            features['num_imports'] = len(imports)
            features['num_imported_dlls'] = len(dlls)
            
            # Признаки наличия специфичных DLL
            dlls_lower = [dll.lower() for dll in dlls]
            features['imports_kernel32'] = 'kernel32.dll' in dlls_lower
            features['imports_user32'] = 'user32.dll' in dlls_lower
            features['imports_advapi32'] = 'advapi32.dll' in dlls_lower
            features['imports_ws2_32'] = 'ws2_32.dll' in dlls_lower
            features['imports_wininet'] = 'wininet.dll' in dlls_lower
            features['imports_urlmon'] = 'urlmon.dll' in dlls_lower
            features['imports_ole32'] = 'ole32.dll' in dlls_lower
            features['imports_oleaut32'] = 'oleaut32.dll' in dlls_lower
            features['imports_shell32'] = 'shell32.dll' in dlls_lower
            features['imports_ntdll'] = 'ntdll.dll' in dlls_lower
            
            # Признаки подозрительных импортов
            suspicious_imports = [
                'virtualalloc', 'virtualprotect', 'createremotethread',
                'writeprocessmemory', 'openprocess', 'regsetvalueex',
                'cryptencrypt', 'cryptdecrypt', 'internetconnect',
                'httpopenrequest', 'urlopenstream', 'shellExecute'
            ]
            
            imports_lower = [imp.lower() for imp in imports]
            for sus_imp in suspicious_imports:
                features[f'imports_{sus_imp}'] = sus_imp in imports_lower
            
            # Статистики по длинам имен импортов
            if imports:
                import_lengths = [len(imp) for imp in imports]
                features['import_name_length_mean'] = np.mean(import_lengths)
                features['import_name_length_max'] = max(import_lengths)
            
        except Exception as e:
            print(f"Ошибка при извлечении признаков импортов: {e}")
            features['num_imports'] = 0
            features['num_imported_dlls'] = 0
        
        return features
    
    def _extract_export_features(self, pe: pefile.PE) -> Dict:
        """Извлекает признаки экспортов."""
        features = {}
        
        try:
            if not hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
                features['num_exports'] = 0
                return features
            
            exports = []
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                if exp.name:
                    exports.append(exp.name.decode('utf-8', errors='ignore'))
            
            features['num_exports'] = len(exports)
            
        except Exception as e:
            features['num_exports'] = 0
        
        return features
    
    def _extract_resource_features(self, pe: pefile.PE) -> Dict:
        """Извлекает признаки ресурсов."""
        features = {}
        
        try:
            if not hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
                features['num_resources'] = 0
                return features
            
            resources = []
            for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                if hasattr(resource_type, 'directory'):
                    for resource_id in resource_type.directory.entries:
                        if hasattr(resource_id, 'directory'):
                            for resource_lang in resource_id.directory.entries:
                                if hasattr(resource_lang, 'data'):
                                    resources.append(resource_lang.data.struct.Size)
            
            features['num_resources'] = len(resources)
            if resources:
                features['resource_size_total'] = sum(resources)
                features['resource_size_mean'] = np.mean(resources)
                features['resource_size_max'] = max(resources)
        
        except Exception as e:
            features['num_resources'] = 0
        
        return features
    
    def _extract_string_features(self, data: bytes) -> Dict:
        """Извлекает признаки строк."""
        import re
        features = {}

        try:
            # re.findall работает в C — в 50-100x быстрее Python-цикла
            raw_strings = re.findall(b'[\x20-\x7e]{4,}', data)
            strings = [s.decode('ascii', errors='ignore') for s in raw_strings]
            
            features['num_strings'] = len(strings)
            
            if strings:
                string_lengths = [len(s) for s in strings]
                features['string_length_mean'] = np.mean(string_lengths)
                features['string_length_max'] = max(string_lengths)
                features['string_length_total'] = sum(string_lengths)
                
                # Поиск подозрительных строк
                suspicious_keywords = [
                    'http://', 'https://', 'ftp://', 'cmd.exe', 'powershell',
                    'reg add', 'reg delete', 'taskkill', 'net user', 'net localgroup',
                    'schtasks', 'wmic', 'vbs', 'javascript', 'eval', 'base64',
                    'encrypt', 'decrypt', 'keylog', 'stealer', 'ransom'
                ]
                
                strings_lower = ' '.join(strings).lower()
                for keyword in suspicious_keywords:
                    features[f'has_string_{keyword.replace("/", "_").replace(" ", "_")}'] = keyword in strings_lower
            
        except Exception as e:
            print(f"Ошибка при извлечении признаков строк: {e}")
        
        return features
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Вычисляет энтропию Шеннона для данных."""
        if not data:
            return 0.0
        
        entropy = 0.0
        length = len(data)
        
        # Подсчет частоты каждого байта
        byte_counts = {}
        for byte in data:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1
        
        # Вычисление энтропии
        for count in byte_counts.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * np.log2(probability)
        
        return entropy
    
    def get_feature_vector(self, features: Dict, feature_list: List[str]) -> np.ndarray:
        """
        Преобразует словарь признаков в вектор для модели.
        
        Args:
            features: Словарь с признаками
            feature_list: Список имен признаков в нужном порядке
            
        Returns:
            NumPy массив с признаками
        """
        vector = []
        for feature_name in feature_list:
            if feature_name in features:
                value = features[feature_name]
                # Преобразуем булевы значения в числа
                if isinstance(value, bool):
                    vector.append(1 if value else 0)
                else:
                    vector.append(float(value) if value is not None else 0.0)
            else:
                vector.append(0.0)
        
        return np.array(vector)

