import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from datetime import datetime
import os
import threading
import subprocess
import time
import locale
import request

locale.setlocale(locale.LC_ALL, '')

def load_and_filter_lots(file_path, percentage):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        filtered_lots = []

        for lot in data:
            for attribute in lot.get("attributes", []):
                if attribute.get("fullName") == "Размер снижения начальной цены" and attribute.get("value", {}).get("name") == percentage:
                    filtered_lots.append(lot)
                    break

        return filtered_lots

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")
        return []

def calculate_novelty(bidd_end_time):
    try:
        end_time = datetime.strptime(bidd_end_time, "%Y-%m-%dT%H:%M:%S.%f%z")
        now = datetime.now(end_time.tzinfo)  # Учитываем временную зону
        return "Новый" if end_time > now else "Старый"
    except Exception:
        return "Не указано"

def show_lots(filtered_lots):
    results_window = tk.Toplevel()
    results_window.title("Результаты сортировки")

    # Рамка для таблицы и скроллбаров
    frame = tk.Frame(results_window)
    frame.pack(fill=tk.BOTH, expand=True)

    # Создаем Treeview с колонками
    tree = ttk.Treeview(frame, columns=("name", "novelty", "link"), show="headings")
    tree.heading("name", text="Название")
    tree.heading("novelty", text="Новизна")
    tree.heading("link", text="Ссылка")

    tree.column("name", width=400, anchor="w")
    tree.column("novelty", width=100, anchor="center")
    tree.column("link", width=500, anchor="w")

    # Создаем вертикальный скроллбар
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # Создаем горизонтальный скроллбар
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)

    # Привязываем скроллбары к таблице
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.pack(fill=tk.BOTH, expand=True)

    def open_link(event):
        selected_item = tree.focus()
        if selected_item:
            values = tree.item(selected_item, "values")
            link = values[2]
            webbrowser.open(link)

    # Заполняем таблицу данными
    for lot in filtered_lots:
        name = lot.get("lotName", "Не указано")
        lot_id = lot.get("id", "Не указано")
        link = f"https://torgi.gov.ru/new/public/lots/lot/{lot_id}?fromRec=false"

        bidd_end_time = lot.get("biddEndTime", "Не указано")
        novelty = calculate_novelty(bidd_end_time)

        tree.insert("", "end", values=(name, novelty, link))

    # Привязываем событие двойного клика для открытия ссылки
    tree.bind("<Double-1>", open_link)

    # Кнопка для закрытия окна
    close_button = tk.Button(results_window, text="Закрыть", command=results_window.destroy)
    close_button.pack(pady=10)


def open_file(percentage):
    file_path = filedialog.askopenfilename(title="Выберите файл JSON", filetypes=[("JSON files", "*.json")])
    if file_path:
        filtered_lots = load_and_filter_lots(file_path, percentage)
        if filtered_lots:
            show_lots(filtered_lots)
        else:
            messagebox.showinfo("Результат", "Подходящих лотов не найдено.")

def get_last_update_time(file_path):
    try:
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    except FileNotFoundError:
        return "Файл не найден"

def run_requests_script(progress_bar, status_label, estimated_time_label):
    def background_task():
        total_pages = 1000
        total_lots = total_pages * 10
        progress_bar["maximum"] = total_lots

        loaded_lots = 0
        start_time = time.time()

        def update_progress(count):
            nonlocal loaded_lots
            loaded_lots += count
            progress_bar["value"] = loaded_lots

            elapsed_time = time.time() - start_time
            remaining_pages = total_pages - (loaded_lots // 10)
            estimated_time = elapsed_time / max(1, (loaded_lots // 10)) * remaining_pages

            status_label.config(text=f"Текущий прогресс: загружено {loaded_lots} записей")
            estimated_time_label.config(
                text=f"Примерное время ожидания: {int(estimated_time // 60)} мин {int(estimated_time % 60)} сек"
            )

        try:
            # Вызываем основную функцию из request.py с передачей callback
            request.main(progress_callback=update_progress)
            status_label.config(text="Загрузка завершена")
            estimated_time_label.config(text="Ожидание завершено.")
        except Exception as e:
            status_label.config(text="Ошибка выполнения скрипта")
            messagebox.showerror("Ошибка", f"Не удалось выполнить скрипт: {e}")
        finally:
            progress_bar.stop()

    threading.Thread(target=background_task, daemon=True).start()


def on_close():
    if messagebox.askokcancel("Выход", "Вы действительно хотите выйти?"):
        stop_event.set()  # Устанавливаем флаг остановки
        root.destroy()


def main():
    global stop_event
    stop_event = threading.Event()

    root = tk.Tk()
    root.title("Сортировка лотов")
    root.style = ttk.Style()
    root.style.theme_use("clam")

    label = tk.Label(root, text="Выберите процент для фильтрации и файл all_lots.json", font=("Arial", 14))
    label.pack(pady=20)

    percentage_var = tk.StringVar(value="30%")

    percentages = ["30%", "60%", "90%", "Свой"]
    percentage_menu = ttk.Combobox(root, textvariable=percentage_var, values=percentages, state="readonly", font=("Arial", 12))
    percentage_menu.pack(pady=10)

    custom_percentage_label = tk.Label(root, text="Введите свой процент:", font=("Arial", 12))
    custom_percentage_entry = tk.Entry(root, font=("Arial", 12))

    def on_percentage_change(event):
        if percentage_var.get() == "Свой":
            custom_percentage_label.pack()
            custom_percentage_entry.pack()
        else:
            custom_percentage_label.pack_forget()
            custom_percentage_entry.pack_forget()

    percentage_menu.bind("<<ComboboxSelected>>", on_percentage_change)

    def sort_button_action():
        percentage = percentage_var.get()
        if percentage == "Свой":
            percentage = custom_percentage_entry.get()
        if percentage:
            open_file(percentage)
        else:
            messagebox.showwarning("Ошибка", "Введите корректный процент.")

    def update_file_info():
        last_update_label.config(text=f"Дата последнего обновления: {get_last_update_time('all_lots.json')}")

    last_update_label = tk.Label(root, text=f"Дата последнего обновления: {get_last_update_time('all_lots.json')}", font=("Arial", 12))
    last_update_label.pack(pady=10)

    reload_button = tk.Button(root, text="Выполнить новую загрузку", command=lambda: run_requests_script(progress_bar, status_label, estimated_time_label), font=("Arial", 12))
    reload_button.pack(pady=10)

    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    progress_bar.pack(pady=10)

    status_label = tk.Label(root, text="", font=("Arial", 12))
    status_label.pack(pady=10)

    estimated_time_label = tk.Label(root, text="Примерное время ожидания: расчет...", font=("Arial", 12))
    estimated_time_label.pack(pady=10)

    sort_button = tk.Button(root, text="Сортировать", command=sort_button_action, font=("Arial", 12))
    sort_button.pack(pady=10)

    exit_button = tk.Button(root, text="Выход", command=root.destroy, font=("Arial", 12))
    exit_button.pack(pady=10)

    root.protocol("WM_DELETE_WINDOW", on_close)  # Устанавливаем обработчик закрытия окна
    root.mainloop()


if __name__ == "__main__":
    main()