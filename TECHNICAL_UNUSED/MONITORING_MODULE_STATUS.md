# ОТ-Монитор — состояние работ по модулю мониторинга источников

**Дата фиксации:** 08.06.2026
**Проект:** ОТ-Монитор MVP
**Папка проекта:** `D:\OT-Monitor-MVP`
**Цель этапа:** перейти от интерфейсной имитации к реальному модулю поиска и загрузки документов из открытых интернет-источников.

## Актуальный статус на 10.06.2026

Текущее состояние модуля мониторинга:

* backend-контур ручной проверки трёх источников работает;
* запуск выполняется через `run_demo_check.bat` или `python run_demo_check.py`;
* автоматическое расписание пока не реализовано;
* кнопка в интерфейсе пока не запускает backend;
* VPN может мешать доступу к Минтруду и Минздраву;
* для демонстрации рекомендуется отключать VPN.

Текущая рабочая цепочка:

```text
run_demo_check.bat → run_demo_check.py → inspect_* → merge_* → data/documents.json + data/check_log.json → MVP
```

---

## 1. Общая цель модуля мониторинга

Модуль мониторинга должен проверять открытые источники нормативной информации, находить новые или потенциально важные документы, сохранять ссылки и метаданные в JSON-структуры, совместимые с MVP «ОТ-Монитор».

Рабочая цепочка:

```text
источник → запрос к сайту → получение HTML/API → извлечение документов → JSON → documents.json → отображение в MVP
```

На данном этапе интерфейс не является главным фокусом. Основная задача — научиться стабильно получать информацию из внешних источников.

---

## 2. Что было сделано по Government.ru

### Источник

```text
https://government.ru/docs/
```

### Проблема

Автоматический Python-запрос к `government.ru/docs/` не сработал:

```text
Read timed out
```

Ошибка возникала как с VPN, так и без VPN.

### Обходной рабочий путь

Страница Government.ru была открыта вручную в браузере и сохранена как HTML:

```text
government_docs.html
```

Затем был создан скрипт:

```text
monitor_government_test.py
```

Он прочитал сохранённый HTML-файл, нашёл ссылки на документы Government.ru и сохранил результат в:

```text
data/government_found_test.json
```

После этого был создан скрипт:

```text
merge_government_to_documents.py
```

Он перенёс найденные документы в основной файл MVP:

```text
data/documents.json
```

Перед этим была создана резервная копия:

```text
data/documents_backup_before_government.json
```

### Результат

В `data/documents.json` было добавлено 10 документов Government.ru.

Интерфейс сначала их не показывал, потому что `app.js` использовал встроенный массив документов, а не `data/documents.json`.

Затем `app.js` был доработан: теперь он загружает документы из:

```text
data/documents.json
```

При этом встроенные демонстрационные документы оставлены как fallback, если JSON не загрузится.

Была создана резервная копия:

```text
app_backup_before_json_load.js
```

### Итог

Документы Government.ru появились в интерфейсе MVP.

---

## 3. Что было сделано по диагностике источников

Создан диагностический скрипт:

```text
check_sources_access.py
```

Он проверяет доступность источников через Python-запросы `requests`.

Проверялись источники:

```text
https://government.ru/docs/
https://publication.pravo.gov.ru/
https://publication.pravo.gov.ru/api/Documents?PageSize=5&Index=1
https://mintrud.gov.ru/docs
https://mchs.gov.ru/
https://rospotrebnadzor.ru/
https://rostrud.gov.ru/
https://minzdrav.gov.ru/documents
https://www.rst.gov.ru/
https://regulation.gov.ru/
https://nac.gov.ru/
```

Скрипт запускался с разными метками:

```text
python check_sources_access.py --label vpn_on
python check_sources_access.py --label vpn_on_2
python check_sources_access.py --label vpn_off
```

Созданы отчёты:

```text
data/source_access_report_vpn_on.json
data/source_access_report_vpn_on_2.json
data/source_access_report_vpn_off.json
```

Для сравнения отчётов создан скрипт:

```text
compare_source_access_reports.py
```

Он создал итоговые файлы:

```text
data/source_access_summary.json
data/source_access_summary.txt
```

---

## 4. Результаты диагностики доступности источников

### Стабильно доступны с VPN и без VPN

```text
mchs.gov.ru
minzdrav.gov.ru/documents
regulation.gov.ru
```

### Лучше работают без VPN

```text
mintrud.gov.ru/docs
rospotrebnadzor.ru
rostrud.gov.ru
www.rst.gov.ru
```

### Пока не работают ни с VPN, ни без VPN

```text
government.ru/docs
publication.pravo.gov.ru
publication.pravo.gov.ru/api
nac.gov.ru
```

### Важный вывод

Python на компьютере работает нормально и способен обращаться к интернету.
Проблема не в Python вообще, а в доступности конкретных сайтов через текущую сетевую схему, VPN, прокси или ограничения самих сайтов.

---

## 5. Что было сделано по Минтруду

### Источник

```text
https://mintrud.gov.ru/docs
```

Диагностика показала, что Минтруд лучше работает без VPN.

Создан разведочный скрипт:

```text
inspect_mintrud_docs.py
```

Он делает следующее:

1. Обращается к `https://mintrud.gov.ru/docs`.
2. Сохраняет HTML-страницу в:

```text
files/saved_documents/mintrud_docs_page.html
```

3. Извлекает ссылки со страницы.
4. Сохраняет общий список найденных ссылок в:

```text
data/mintrud_links_inspection.json
```

После первого запуска было видно, что файл содержит как реальные документы, так и служебные ссылки, например:

```text
Форма обратной связи
Документы
```

После этого скрипт был доработан: добавлена мягкая фильтрация.

Теперь дополнительно формируются файлы:

```text
data/mintrud_documents_filtered.json
data/mintrud_links_rejected.json
```

### Логика фильтрации

В `data/mintrud_documents_filtered.json` сохраняются ссылки, похожие на реальные документы, если URL содержит:

```text
/docs/mintrud/orders/
```

или

```text
/docs/agreements/
```

Отброшенные ссылки сохраняются отдельно в:

```text
data/mintrud_links_rejected.json
```

Это сделано, чтобы не потерять потенциально нужные ссылки.

### Результат

Фильтрация Минтруда отработала.
Получен очищенный список документов Минтруда.

---

## 11. Результат подключения Минтруда к MVP

Дата фиксации: 09.06.2026

Создан скрипт `merge_mintrud_to_documents.py`.

Скрипт выполнил перенос документов из:

```text
data/mintrud_documents_filtered.json
```

в основной файл MVP:

```text
data/documents.json
```

Результат запуска:

- найдено документов Минтруда: 10
- добавлено новых документов: 10
- пропущено дублей: 0
- создана запись проверки в `data/check_log.json`

Проверка через PowerShell подтвердила, что в `data/documents.json` есть 10 записей с источником `"Минтруд России"`.

MVP был запущен через локальный сервер:

```text
python -m http.server 8000
```

В браузере по адресу `http://localhost:8000` документы Минтруда отображаются в интерфейсе.

Текущий результат:
цепочка Минтруд → filtered JSON → documents.json → check_log.json → MVP работает.

Дополнительная проверка:
Повторный запуск merge_mintrud_to_documents.py выполнен успешно.
Результат повторного запуска:
- найдено документов Минтруда: 10
- добавлено новых документов: 0
- пропущено как дубли: 10

Вывод:
защита от дублей работает, повторный запуск не засоряет data/documents.json.

Следующий возможный шаг:
проверить повторный запуск `merge_mintrud_to_documents.py` на отсутствие дублей или перейти к следующему стабильному источнику, например МЧС, Минздрав или `regulation.gov.ru`.

---

## 12. Результат подключения МЧС к MVP

Дата фиксации: 09.06.2026

Источник:
https://mchs.gov.ru/dokumenty/vse-dokumenty

Создан разведочный скрипт:
`inspect_mchs_docs.py`

Скрипт выполняет:
- запрос к странице МЧС;
- сохранение HTML в `files/saved_documents/mchs_docs_page.html`;
- сохранение всех ссылок в `data/mchs_links_inspection.json`;
- сохранение файлов-вложений в `data/mchs_document_files.json`;
- сохранение отклонённых ссылок в `data/mchs_links_rejected.json`;
- сохранение отфильтрованных страниц документов в `data/mchs_documents_filtered.json`.

Первый запуск нашёл:
- всего ссылок: 184
- файлов документов: 10
- после смысловой фильтрации страниц документов: 1

В filtered осталась запись:
`"Положение о Департаменте надзорной деятельности и профилактической работы МЧС России"`

Создан скрипт:
`merge_mchs_to_documents.py`

Скрипт перенёс документ МЧС из:
`data/mchs_documents_filtered.json`

в основной файл MVP:
`data/documents.json`

Также создана запись проверки в:
`data/check_log.json`

Проверка PowerShell подтвердила:
- `"МЧС России"` есть в `data/documents.json`
- `"МЧС России"` есть в `data/check_log.json`

MVP был обновлён в браузере, документ МЧС появился в разделе последних найденных документов.

Дополнительная проверка:
повторный запуск `merge_mchs_to_documents.py` выполнен успешно.
Новых документов добавлено: 0.
Дублей пропущено: 1.

Вывод:
цепочка МЧС → filtered JSON → documents.json → check_log.json → MVP работает.
Защита от дублей работает.

---

## 13. Результат подключения Минздрава к MVP

Дата фиксации: 09.06.2026

Источник:
https://minzdrav.gov.ru/documents

Важное сетевое условие:
Минздрав корректно открылся и отработал без VPN.
При работе с VPN ранее возникала ошибка:
Read timed out

Создан разведочный скрипт:
`inspect_minzdrav_docs.py`

Скрипт выполняет:
- запрос к странице Минздрава;
- сохранение HTML в `files/saved_documents/minzdrav_docs_page.html`;
- сохранение всех ссылок в `data/minzdrav_links_inspection.json`;
- сохранение отклонённых ссылок в `data/minzdrav_links_rejected.json`;
- сохранение отфильтрованных ссылок в `data/minzdrav_documents_filtered.json`.

После доработки фильтрации результат запуска:
- всего ссылок найдено: 85
- ссылок попало в filtered: 3
- ссылок попало в rejected: 82

Создан скрипт:
`merge_minzdrav_to_documents.py`

Скрипт перенёс документы Минздрава из:
`data/minzdrav_documents_filtered.json`

в основной файл MVP:
`data/documents.json`

Также создана запись проверки в:
`data/check_log.json`

Результат переноса:
- документов найдено в filtered: 3
- добавлено новых документов: 3
- пропущено как дубли: 0

Проверка PowerShell подтвердила:
- `"Минздрав России"` есть в `data/documents.json`
- `"Минздрав России"` есть в `data/check_log.json`

MVP был запущен через локальный сервер:
`python -m http.server 8000`

В браузере по адресу:
`http://localhost:8000`

записи Минздрава появились в интерфейсе MVP.

Важное замечание:
Минздрав технически подключён к цепочке мониторинга, но смысловая релевантность найденных документов пока неидеальна и требует отдельной доработки фильтрации.

Вывод:
цепочка Минздрав → filtered JSON → documents.json → check_log.json → MVP работает.
Для дальнейшей работы нужно улучшать качество тематического отбора документов Минздрава.

---

## 6. Важные созданные файлы

### Диагностика источников

```text
check_sources_access.py
compare_source_access_reports.py
data/source_access_report_vpn_on.json
data/source_access_report_vpn_on_2.json
data/source_access_report_vpn_off.json
data/source_access_summary.json
data/source_access_summary.txt
```

### Government.ru

```text
government_docs.html
monitor_government_test.py
data/government_found_test.json
merge_government_to_documents.py
data/documents_backup_before_government.json
```

### Минтруд

```text
inspect_mintrud_docs.py
files/saved_documents/mintrud_docs_page.html
data/mintrud_links_inspection.json
data/mintrud_documents_filtered.json
data/mintrud_links_rejected.json
```

### Интерфейс и резервные копии

```text
app.js
app_backup_before_json_load.js
data/documents.json
```

---

## 7. Что пока НЕ сделано

Пока не сделано:

1. Автоматическое добавление документов Минтруда в `data/documents.json`.
2. Запись результата проверки Минтруда в `data/check_log.json`.
3. Подключение Python-скрипта к кнопке «Проверить сейчас».
4. Автоматическое скачивание PDF или HTML-страниц каждого документа.
5. Тематическая фильтрация по ключевым словам охраны труда.
6. Сопоставление документов Минтруда с типами внутренних документов.
7. Автоматическое расписание проверки.
8. Полноценная обработка API `publication.pravo.gov.ru`.
9. Промышленная архитектура мониторинга.

---

## 8. Что важно помнить следующему диалогу

Пользователь не является программистом.
Нужно работать очень медленно, пошагово и без перегрузки теорией.

Правильный формат работы:

1. Сначала кратко объяснить, что делаем и зачем.
2. Дать один маленький шаг.
3. Ждать подтверждения пользователя.
4. Не давать сразу много команд.
5. Если работа идёт через Codex, давать готовый текст задания для вставки.
6. Перед изменением важных файлов делать резервные копии.
7. Не трогать интерфейс без необходимости.
8. Основной фокус — реальный модуль мониторинга источников.

При работе с Codex желательно использовать режим:

```text
Ask for approval
```

Codex может писать код, но запуск скриптов с отключённым VPN пользователь должен делать вручную через PowerShell/терминал.

---

## 9. Следующий логичный шаг

Следующий этап лучше начать с Минтруда.

Рекомендуемый следующий шаг:

```text
data/mintrud_documents_filtered.json
→ преобразовать в формат documents.json
→ добавить в data/documents.json без дублей
→ записать проверку в data/check_log.json
→ проверить отображение в MVP
```

Но перед добавлением в основной MVP нужно сначала открыть и проверить:

```text
data/mintrud_documents_filtered.json
```

Нужно убедиться, что там действительно только документы Минтруда, без служебных ссылок.

После этого создать отдельный безопасный скрипт:

```text
merge_mintrud_to_documents.py
```

Он должен:

1. Читать `data/mintrud_documents_filtered.json`.
2. Преобразовывать поля в формат MVP.
3. Добавлять только новые документы в `data/documents.json`.
4. Не добавлять дубли по URL.
5. Создать или обновить запись в `data/check_log.json`.
6. Не менять `app.js`, `index.html`, `style.css`.

---

## 10. Текущий главный результат

На 08.06.2026 получен первый работающий путь реального мониторинга:

```text
внешний источник → Python → JSON → documents.json → интерфейс MVP
```

Government.ru был подключён через сохранённый HTML.
Минтруд успешно читается живым Python-запросом без VPN и уже выдаёт очищенный список документов.

Главная задача следующего этапа — превратить найденные документы Минтруда в полноценные карточки MVP.
