"""
깨진 OTF 폰트 파일을 검사하고 삭제하는 프로그램
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

try:
    from fontTools.ttLib import TTFont
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
except ImportError:
    print("fontTools가 필요합니다. 설치하세요: pip install fonttools")
    sys.exit(1)


class FontChecker:
    def __init__(self, directory: str, dry_run: bool = True, max_workers: int = 8):
        self.directory = Path(directory)
        self.dry_run = dry_run
        self.max_workers = max_workers
        self.corrupted_fonts = []
        self.valid_fonts = []
        self.lock = Lock()
        self.processed_count = 0
        self.total_count = 0
        
    def find_otf_files(self) -> List[Path]:
        """디렉토리에서 OTF 파일들을 찾습니다."""
        otf_files = []
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.lower().endswith('.otf'):
                    otf_files.append(Path(root) / file)
        return otf_files
    
    def check_font_integrity(self, font_path: Path) -> Tuple[bool, str]:
        """
        폰트 파일의 무결성을 빠르게 검사합니다.
        """
        try:
            # 1. 파일 크기 체크
            file_size = font_path.stat().st_size
            if file_size < 1024:  # 1KB 미만
                return False, "파일이 너무 작음"
            
            # 2. 기본적인 TTFont 로딩 테스트
            font = TTFont(font_path, lazy=True)
            
            # 3. 필수 테이블만 빠르게 체크
            required_tables = ['head', 'name', 'cmap']
            for table in required_tables:
                if table not in font:
                    font.close()
                    return False, f"필수 테이블 누락: {table}"
            
            # 4. head 테이블 매직넘버만 체크
            try:
                head = font['head']
                if head.magicNumber != 0x5F0F3CF5:
                    font.close()
                    return False, "잘못된 매직넘버"
            except:
                font.close()
                return False, "head 테이블 읽기 실패"
            
            # 5. name 테이블에서 폰트 이름 체크
            try:
                name_table = font['name']
                valid_name = False
                for record in name_table.names:
                    if record.nameID == 1:
                        name_str = record.toUnicode()
                        if name_str and len(name_str.strip()) > 0:
                            # 정상적인 문자가 포함되어 있는지
                            if any(c.isalnum() for c in name_str):
                                valid_name = True
                                break
                
                if not valid_name:
                    font.close()
                    return False, "유효한 폰트 이름 없음"
            except:
                font.close()
                return False, "name 테이블 읽기 실패"
            
            font.close()
            return True, "정상"
            
        except Exception as e:
            return False, f"로딩 실패: {str(e)[:50]}"
    
    def get_font_info(self, font_path: Path) -> dict:
        """폰트 파일의 정보를 빠르게 가져옵니다."""
        try:
            font = TTFont(font_path, lazy=True)
            
            # 폰트 이름 빠르게 추출
            font_name = "알 수 없음"
            if 'name' in font:
                name_table = font['name']
                for record in name_table.names:
                    if record.nameID == 1:
                        try:
                            font_name = record.toUnicode()[:50]  # 길이 제한
                            break
                        except:
                            continue
            
            font.close()
            return {
                'name': font_name,
                'size': font_path.stat().st_size,
                'path': str(font_path)
            }
        except:
            return {
                'name': "읽기 실패",
                'size': font_path.stat().st_size if font_path.exists() else 0,
                'path': str(font_path)
            }
    
    def process_single_font(self, font_path: Path) -> None:
        """단일 폰트 파일을 처리합니다."""
        is_valid, error_msg = self.check_font_integrity(font_path)
        font_info = self.get_font_info(font_path)
        
        with self.lock:
            self.processed_count += 1
            progress = (self.processed_count / self.total_count) * 100
            
            if is_valid:
                self.valid_fonts.append((font_path, font_info))
                status = "✓ 정상"
            else:
                self.corrupted_fonts.append((font_path, font_info, error_msg))
                status = "✗ 손상됨"
            
            print(f"[{self.processed_count}/{self.total_count}] ({progress:.1f}%) {font_path.name} - {status}")
            if not is_valid:
                print(f"  └─ {error_msg}")
    
    def scan_fonts(self) -> None:
        """모든 OTF 파일을 멀티스레드로 스캔합니다."""
        otf_files = self.find_otf_files()
        
        if not otf_files:
            print(f"'{self.directory}'에서 OTF 파일을 찾을 수 없습니다.")
            return
        
        self.total_count = len(otf_files)
        print(f"총 {self.total_count}개의 OTF 파일을 {self.max_workers}개 스레드로 검사합니다...\n")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 작업을 큐에 제출
            futures = [executor.submit(self.process_single_font, font_path) for font_path in otf_files]
            
            # 완료된 작업들을 처리
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"오류 발생: {e}")
        
        print(f"\n검사 완료! {self.processed_count}/{self.total_count} 파일 처리됨")
    
    def display_results(self) -> None:
        """검사 결과를 표시합니다."""
        print("=" * 60)
        print("검사 결과 요약")
        print("=" * 60)
        print(f"정상 폰트: {len(self.valid_fonts)}개")
        print(f"손상된 폰트: {len(self.corrupted_fonts)}개")
        print()
        
        if self.corrupted_fonts:
            print("손상된 폰트 목록:")
            print("-" * 60)
            total_size = 0
            for font_path, font_info, error_msg in self.corrupted_fonts:
                size_mb = font_info['size'] / (1024 * 1024)
                total_size += font_info['size']
                print(f"파일: {font_path.name}")
                print(f"경로: {font_info['path']}")
                print(f"크기: {size_mb:.2f} MB")
                print(f"오류: {error_msg}")
                print("-" * 40)
            
            print(f"총 손상된 파일 크기: {total_size / (1024 * 1024):.2f} MB")
    
    def delete_corrupted_fonts(self) -> None:
        """손상된 폰트 파일들을 삭제합니다."""
        if not self.corrupted_fonts:
            print("삭제할 손상된 폰트가 없습니다.")
            return
        
        if self.dry_run:
            print("\n[DRY RUN] 실제로는 삭제하지 않습니다.")
            print("실제 삭제를 원하면 --delete 옵션을 사용하세요.")
            return
        
        print(f"\n{len(self.corrupted_fonts)}개의 손상된 폰트를 삭제합니다...")
        
        deleted_count = 0
        for font_path, font_info, error_msg in self.corrupted_fonts:
            try:
                os.remove(font_path)
                print(f"삭제됨: {font_path.name}")
                deleted_count += 1
            except OSError as e:
                print(f"삭제 실패: {font_path.name} - {e}")
        
        print(f"\n총 {deleted_count}개 파일이 삭제되었습니다.")


def main():
    parser = argparse.ArgumentParser(
        description="깨진 OTF 폰트 파일을 검사하고 삭제합니다."
    )
    parser.add_argument(
        "directory",
        help="검사할 디렉토리 경로"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="손상된 폰트 파일을 실제로 삭제 (기본값: dry run)"
    )
    parser.add_argument(
        "--threads", "-t",
        type=int,
        default=8,
        help="사용할 스레드 수 (기본값: 8)"
    )
    
    args = parser.parse_args()
    
    # 디렉토리 존재 확인
    if not os.path.isdir(args.directory):
        print(f"오류: '{args.directory}'는 유효한 디렉토리가 아닙니다.")
        sys.exit(1)
    
    # 폰트 검사 실행
    checker = FontChecker(args.directory, dry_run=not args.delete, max_workers=args.threads)
    
    print(f"폰트 검사 시작: {args.directory}")
    print(f"모드: {'실제 삭제' if args.delete else 'DRY RUN (삭제하지 않음)'}")
    print(f"스레드 수: {args.threads}")
    print()
    
    checker.scan_fonts()
    checker.display_results()
    
    if checker.corrupted_fonts:
        print("\n" + "=" * 60)
        if not args.delete:
            print("실제 삭제를 원하면 다음 명령어를 실행하세요:")
            print(f"python {sys.argv[0]} '{args.directory}' --delete")
        else:
            response = input("\n손상된 폰트를 삭제하시겠습니까? (y/N): ")
            if response.lower() == 'y':
                checker.delete_corrupted_fonts()
            else:
                print("삭제가 취소되었습니다.")


if __name__ == "__main__":
    main()