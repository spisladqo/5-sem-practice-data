import sys
import statistics

def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    # Извлекаем все числа (разделители – пробелы и переводы строк)
    nums = []
    for token in text.split():
        try:
            nums.append(float(token))
        except ValueError:
            pass

    if not nums:
        print("Нет чисел для обработки")
        return

    print(f"Количество чисел: {len(nums)}")
    print(f"Минимум:  {min(nums):.4f}")
    print(f"Максимум: {max(nums):.4f}")
    print(f"Среднее:  {statistics.mean(nums):.4f}")
    print(f"Медиана:  {statistics.median(nums):.4f}")

if __name__ == "__main__":
    main()