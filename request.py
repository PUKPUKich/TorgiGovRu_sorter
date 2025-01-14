import requests
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def fetch_page_data(base_url, params, page, progress_callback=None, retries=3, timeout=60):
    """Загружает данные одной страницы с повторными попытками."""
    for attempt in range(retries):
        try:
            params["page"] = page
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()  # Проверяем успешность запроса

            if response.headers.get("Content-Type", "").startswith("application/json"):
                page_data = response.json()
                if progress_callback:
                    progress_callback(10)  # Уведомляем о прогрессе (+10 записей)
                return page_data.get("content", [])  # Возвращаем только содержимое
            else:
                print(f"Некорректный ответ на странице {page}: {response.text[:200]}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при загрузке страницы {page}, попытка {attempt + 1}: {e}")
            time.sleep(2)  # Задержка перед повтором
    print(f"Не удалось загрузить страницу {page} после {retries} попыток.")
    return []

def save_partial_data(data, output_directory, filename="all_lots.json"):
    """Сохраняет данные в файл."""
    file_path = os.path.join(output_directory, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"Данные успешно сохранены в файл: {file_path}")
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

def fetch_data(base_url, params, pages, progress_callback=None, output_directory=".", max_workers=10):
    all_data = []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Создаем задания для всех страниц
            futures = [
                executor.submit(fetch_page_data, base_url, params.copy(), page, progress_callback)
                for page in range(1, pages + 1)
            ]

            for future in as_completed(futures):
                page_data = future.result()
                if page_data:  # Если данные есть, добавляем
                    all_data.extend(page_data)

        # Сохраняем итоговые данные
        save_partial_data(all_data, output_directory, filename="all_lots.json")

    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")

def main(progress_callback=None):
    """Основной вход в скрипт request.py."""
    # URL для запроса
    base_url = "https://torgi.gov.ru/new/api/public/lotcards/search"

    # Параметры запроса
    params = {
        "lotStatus": "PUBLISHED,APPLICATIONS_SUBMISSION",
        "matchPhrase": "false",
        "byFirstVersion": "true",
        "withFacets": "false",
        "size": 10,
        "sort": "firstVersionPublicationDate,desc"
    }

    # Количество страниц для загрузки
    pages = 1000

    # Загружаем данные и сохраняем в файл
    fetch_data(base_url, params, pages, progress_callback=progress_callback, max_workers=5)
