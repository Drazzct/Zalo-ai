import json

def update_notebook(path):
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    updated = False
    for cell in nb['cells']:
        src = ''.join(cell.get('source', []))
        if 'Zalo-ai.zip' in src and cell.get('cell_type') == 'code':
            new_code = [
                'import os\n',
                'REPO_URL = "https://github.com/Drazzct/Zalo-ai.git"\n',
                'TARGET_DIR = "/content/Zalo-ai"\n',
                '\n',
                'if os.path.exists("/content"):\n',
                '    if not os.path.exists(TARGET_DIR):\n',
                '        print(f"📦 Đang clone mã nguồn mới nhất từ {REPO_URL}...")\n',
                '        !git clone {REPO_URL} {TARGET_DIR}\n',
                '    else:\n',
                '        print(f"🔄 Thư mục {TARGET_DIR} đã tồn tại, đang tự động đồng bộ (git pull) bản mới nhất...")\n',
                '        %cd {TARGET_DIR}\n',
                '        !git fetch origin main && git reset --hard origin/main\n',
                '    %cd {TARGET_DIR}\n',
                'else:\n',
                '    print(f"ℹ️ Đang chạy trên môi trường local: {os.getcwd()}")\n',
                '\n',
                'print("✅ Thư mục làm việc hiện tại:", os.getcwd())\n',
                '!git log -1 --oneline\n'
            ]
            cell['source'] = new_code
            updated = True
            break
            
    if updated:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        print(f'✅ Updated {path}')
    else:
        print(f'⚠️ No matching cell found in {path}')

update_notebook('notebooks/colab_run_benchmark.ipynb')
update_notebook('notebooks/test_converted_questions.ipynb')
