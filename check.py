import os

def count_lines_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"Xəta: {filepath} - {e}")
        return 0

def count_total_lines_in_current_directory(extensions=[".py", ".txt"]):
    total_lines = 0
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for root, _, files in os.walk(current_dir):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, file)
                line_count = count_lines_in_file(full_path)
                print(f"{full_path}: {line_count} sətir")
                total_lines += line_count
    return total_lines

if __name__ == "__main__":
    total = count_total_lines_in_current_directory()
    print(f"\n✅ Layihədəki bütün fayllarda cəmi sətir sayı: {total}")
