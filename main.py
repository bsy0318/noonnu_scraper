import os
import subprocess
import requests
import glob
from pathlib import Path
from fontTools.ttLib import TTFont
import shutil

def get_user_repos(username, token=None):
    """GitHub API를 사용해서 사용자의 모든 레포지토리 목록을 가져옴"""
    repos = []
    page = 1
    
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"API 요청 실패: {response.status_code}")
            break
            
        data = response.json()
        if not data:
            break
            
        repos.extend(data)
        page += 1
    
    return repos

def clone_repo(repo_url, destination_dir):
    """레포지토리를 지정된 디렉토리에 클론"""
    try:
        subprocess.run(['git', 'clone', repo_url, destination_dir], 
                      check=True, capture_output=True)
        print(f"✓ 클론 완료: {repo_url}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 클론 실패: {repo_url} - {e}")
        return False

def update_repo(repo_dir):
    """기존 레포지토리 업데이트"""
    try:
        subprocess.run(['git', 'pull'], cwd=repo_dir, check=True, capture_output=True)
        print(f"✓ 업데이트 완료: {repo_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 업데이트 실패: {repo_dir} - {e}")
        return False

def convert_font_to_otf(font_path, output_dir):
    """woff/woff2 파일을 otf로 변환"""
    try:
        # 폰트 파일 로드
        font = TTFont(font_path)
        
        # 출력 파일명 설정
        font_name = Path(font_path).stem
        otf_path = os.path.join(output_dir, f"{font_name}.otf")
        
        # 이미 변환된 파일이 있으면 스킵
        if os.path.exists(otf_path):
            print(f"  ⚠️  이미 존재함: {otf_path}")
            return True
        
        # TTF/OTF 포맷으로 저장 (OpenType 형식)
        # woff/woff2에서 변환할 때는 flavor를 None으로 설정
        font.flavor = None
        font.save(otf_path)
        print(f"  ✓ 변환 완료: {font_path} → {otf_path}")
        return True
        
    except Exception as e:
        print(f"  ✗ 변환 실패: {font_path} - {e}")
        # 대안: ttf로 저장 시도
        try:
            font_name = Path(font_path).stem
            ttf_path = os.path.join(output_dir, f"{font_name}.ttf")
            if not os.path.exists(ttf_path):
                font = TTFont(font_path)
                font.flavor = None
                font.save(ttf_path)
                print(f"  ✓ TTF로 변환 완료: {font_path} → {ttf_path}")
                return True
        except Exception as e2:
            print(f"  ✗ TTF 변환도 실패: {font_path} - {e2}")
        return False

def find_font_files(directory):
    """디렉토리에서 모든 woff, woff2 파일 찾기"""
    font_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.woff', '.woff2')):
                font_files.append(os.path.join(root, file))
    return font_files

def ask_user_choice(message, default='y'):
    """사용자에게 선택지를 제공"""
    choices = '[Y/n]' if default.lower() == 'y' else '[y/N]'
    while True:
        choice = input(f"{message} {choices}: ").strip().lower()
        if not choice:
            return default.lower() == 'y'
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print("y 또는 n을 입력해주세요.")

def main():
    # 설정
    USERNAME = "projectnoonnu"
    print("Token 발급 방법: Github 프로필 설정 > Settings > Developer Settings > Personal access tokens (classic) > Tokens (classic)")
    GITHUB_TOKEN = input("GitHub 토큰 (선택사항, 엔터로 스킵): ").strip() or None
    BASE_DIR = "./projectnoonnu_repos"
    CONVERTED_DIR = "./projectnoonnu_converted_fonts"
    
    # 기존 폴더 처리
    if os.path.exists(BASE_DIR):
        print(f"\n⚠️  '{BASE_DIR}' 폴더가 이미 존재합니다.")
        if ask_user_choice("기존 레포지토리들을 업데이트하시겠습니까?"):
            update_existing = True
        else:
            if ask_user_choice("기존 폴더를 삭제하고 새로 다운로드하시겠습니까?"):
                shutil.rmtree(BASE_DIR)
                print(f"✓ 기존 폴더 삭제 완료")
                update_existing = False
            else:
                print("기존 폴더를 그대로 사용합니다.")
                update_existing = False
    else:
        update_existing = False
    
    # 디렉토리 생성
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    
    print(f"\n🔍 projectnoonnu의 레포지토리 목록을 가져오는 중...")
    repos = get_user_repos(USERNAME, GITHUB_TOKEN)
    
    if not repos:
        print("레포지토리를 찾을 수 없습니다.")
        return
    
    print(f"📦 총 {len(repos)}개의 레포지토리를 발견했습니다.\n")
    
    # 각 레포지토리 클론 또는 업데이트
    processed_repos = []
    for repo in repos:
        repo_name = repo['name']
        repo_url = repo['clone_url']
        repo_dir = os.path.join(BASE_DIR, repo_name)
        
        if os.path.exists(repo_dir):
            if update_existing:
                print(f"🔄 업데이트 중: {repo_name}")
                if update_repo(repo_dir):
                    processed_repos.append(repo_dir)
            else:
                print(f"⚠️  이미 존재함: {repo_name}")
                processed_repos.append(repo_dir)
        else:
            if clone_repo(repo_url, repo_dir):
                processed_repos.append(repo_dir)
    
    # 모든 처리된 레포에서 폰트 파일 찾기 및 변환
    print(f"\n🔍 폰트 파일(woff, woff2)을 찾는 중...")
    total_font_files = 0
    converted_files = 0
    
    for repo_dir in processed_repos:
        repo_name = os.path.basename(repo_dir)
        font_files = find_font_files(repo_dir)
        
        if font_files:
            print(f"\n📁 {repo_name}에서 {len(font_files)}개의 폰트 파일 발견:")
            total_font_files += len(font_files)
            
            # 레포별 변환 디렉토리 생성
            repo_converted_dir = os.path.join(CONVERTED_DIR, repo_name)
            os.makedirs(repo_converted_dir, exist_ok=True)
            
            for font_file in font_files:
                if convert_font_to_otf(font_file, repo_converted_dir):
                    converted_files += 1
    
    # 결과 요약
    print(f"\n📊 변환 완료!")
    print(f"   • 처리된 레포지토리: {len(processed_repos)}개")
    print(f"   • 발견된 폰트 파일: {total_font_files}개")
    print(f"   • 변환 성공: {converted_files}개")
    print(f"   • 변환된 파일 위치: {CONVERTED_DIR}")
    
    if total_font_files > 0:
        print(f"\n💡 변환 성공률: {converted_files/total_font_files*100:.1f}%")

if __name__ == "__main__":
    # 필요한 패키지 설치 확인
    try:
        import requests
        from fontTools.ttLib import TTFont
    except ImportError as e:
        print(f"필요한 패키지가 설치되지 않았습니다: {e}")
        print("다음 명령으로 설치하세요:")
        print("pip install requests fonttools[woff] brotli")
        exit(1)
    
    main()