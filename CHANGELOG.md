# Changelog

Все значимые изменения проекта документируются здесь.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).
Проект придерживается [семантического версионирования](https://semver.org/lang/ru/).

## [Unreleased] — ветка `1-new-interface`

Изменения относительно ветки `master` (8 коммитов, 08.11.2026–15.11.2026):
`d3b2f15`, `cf01ec5`, `2eba554`, `4b6751c`, `a21a068`, `d0f3fa1`, `0cc6691`, `372a403`.

### Добавлено

#### Спецификация новой версии

- Описание новой версии проекта: `specs/project.md`, JSON-схема данных `specs/schema.json`, пример данных `specs/example.jsonl`.
- Дизайн-макеты веб-интерфейса: `specs/design/prescriptions_overview.png`, `prescriptions_add.png`, `prescriptions_edit.png`, `prescriptions_detail.png`.
- Логотипы проекта: `specs/logo.png`, `specs/logo_example.png`, `specs/logo_tg.png`.

#### Backend: REST API на FastAPI

- Новый пакет `backend/` — REST API для управления назначениями:
  - `backend/models.py` — Pydantic-модели (`PrescriptionCreate`, `PrescriptionUpdate` и др.).
  - `backend/storage.py` — файловое хранилище в формате JSONL (`data/prescriptions.jsonl`, `data/deleted.jsonl`).
  - `backend/calculator.py` — расчёт дат: окончание препарата, следующая дата получения, рекомендуемая дата нового назначения (запасы `PRESCRIPTION_DELTA_DAYS = 14`, `PICK_UP_DELTA_DAYS = 7`).
  - `backend/report.py` — текстовый отчёт `/api/quando/`: когда получать новое назначение и следующее лекарство.
  - `backend/reminder.py` — генерация HTML-напоминаний на конкретную дату (по `next_date` назначения и `next_pick_up_date` препарата) для `/api/reminder/`.
  - `backend/service.py`, `backend/routes.py`, `backend/main.py` — сервисный слой и эндпоинты с префиксом `/api`:
    - `GET/POST /api/prescriptions/` — список и создание назначений;
    - `GET/PUT/DELETE /api/prescriptions/{id}/` — чтение, полная замена и удаление;
    - `GET /api/prescriptions/backup/` и `GET /api/prescriptions/backup-deleted/` — скачивание бэкапов (NDJSON);
    - `GET /api/quando/` — текстовый отчёт;
    - `GET /api/reminder/` — напоминание на сегодня (404, если совпадений нет).
- Документация API: `backend/README.md`.
- Тесты (pytest): `backend/tests/test_api.py`, `test_calculator.py`, `test_report.py`, `test_reminder.py`, `conftest.py`.
- Конфигурация pytest в `pyproject.toml` (`pythonpath`, `testpaths = backend/tests`), группа dev-зависимостей с `pytest`.

#### Frontend: веб-интерфейс

- SPA в `frontend/` без сборщиков и фреймворков:
  - `index.html`, `css/styles.css` — разметка и стили (адаптивный дизайн по макетам);
  - `js/router.js` — хэш-роутинг, `js/app.js` — точка входа, `js/api.js` — клиент REST API, `js/format.js` — форматирование дат/чисел, `js/ui.js` — общие UI-компоненты;
  - `js/views/list.js`, `views/add.js`, `views/edit.js` — экраны списка назначений, добавления и редактирования/детальной карточки.
- Набор SVG-иконок в `frontend/assets/icons/` и логотип `frontend/assets/logo.png`.

#### Telegram-бот: новые команды и режим напоминаний

- `/quando` (кириллический алиас `/когда`) — отчёт по назначениям из API: когда получать новое назначение и следующее лекарство.
- `/backup` — скачивание бэкапа данных: альбом из файлов `prescriptions` и `deleted` (один документ или заметка, если файлов пока нет).
- Режим `reminder`: `uv run python bot.py reminder` — разовая отправка напоминания в группу `CHAT_ID` (для запуска из крона). Бот делает один запрос к `GET /api/reminder/`; при отсутствии напоминаний (404) молча завершается, ошибки пишутся в лог и не ломают вызов из крона.

#### Конфигурация

- Новые переменные окружения (`.env.example`):
  - `API_URL` — адрес REST API без префикса `/api` (по умолчанию `http://127.0.0.1:8000`); нужен командам `/quando`, `/backup` и напоминаниям;
  - `CHAT_ID` — ID группы для напоминаний;
  - `TG_USERNAME` — имя пользователя в префиксе напоминания;
  - `SITE_URL` — адрес сайта, отображаемый ботом.
- Новые настройки в `settings.py`: пути хранилища (`DATA_PATH`, `PRESCRIPTIONS_PATH`, `DELETED_PATH`) и переменные выше.
- Новые константы в `constants.py`: `PRESCRIPTION_DELTA_DAYS`, `PICK_UP_DELTA_DAYS`, `DELETED_AT`, `API_PREFIX`.

### Изменено

- `README.md` — описаны новые переменные окружения, запуск backend/frontend, режим `reminder` с примером cron-расписания; в таблицу команд бота добавлены `/quando` и `/backup`.
- `pyproject.toml` — добавлены зависимости `fastapi`, `uvicorn[standard]`, `httpx`; существующие зависимости закреплены точными версиями (`python-decouple==3.8`, `python-telegram-bot==22.8`, `pyyaml==6.0.3`).
- `bot.py` — переработан: вместо локальных данных (`calculate.py`/`parsers.py`) использует REST API, добавлены команды `/quando` и `/backup`, режим разовой отправки напоминаний.
- `.gitignore` — добавлены исключения: `data/` (файлы хранилища JSONL), `deploy/`, `.kilo/`.
- `specs/project.md`, `specs/schema.json` — спецификация приведена в соответствие с реализацией.
- `uv.lock` — обновлён под новый набор зависимостей.

### Удалено

- Старый интерфейс бота для работы с локальным YAML-файлом: команды `/today`, `/report`, `/date`, `/new` (заменены веб-интерфейсом, REST API и командами `/quando`, `/backup`).
- `calculate.py` — старый модуль локального расчёта (заменён `backend/calculator.py` и REST API).
- `parsers.py` — старый парсер текстовых сообщений (заменён веб-интерфейсом и API).
- `specs/example.json` — заменён на `specs/example.jsonl` (формат хранения JSONL).

---

## Текущее состояние `master` (версия 0.1.0, не выпущена)

- Telegram-бот на `python-telegram-bot`: команды `/help`, `/hello`, `/today`, `/report`, `/date`, `/new`, `/chat_id` — расчёт остатка препаратов по дате получения и нормам приёма из локального YAML-файла `conditions.yml`.
- Модули `calculate.py` (расчёты и отчёты) и `parsers.py` (разбор текстовых сообщений бота).

[Unreleased]: https://github.com/ansakoy/quando/compare/master...1-new-interface
