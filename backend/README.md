# Backend (Quando API)

REST API на **FastAPI** для управления назначениями (prescriptions): CRUD + автоматический расчёт дат окончания препаратов и даты следующего визита к врачу. Данные хранятся в NDJSON-файлах `data/prescriptions.jsonl` (активные записи) и `data/deleted.jsonl` (архив удалённых).

## Запуск

Из корня проекта:

```bash
uv run python -m backend.main   # http://127.0.0.1:8000
uv run pytest backend/tests     # тесты
```

Интерактивная документация Swagger: `http://127.0.0.1:8000/docs`.

## Методы API

Базовый префикс — `/api`. Все даты — в формате `YYYY-MM-DD`.

| Метод | Путь | Код успеха | Назначение |
|-------|------|-----------|------------|
| `GET` | `/api/prescriptions/` | 200 | Список всех назначений (сортировка по `id` по убыванию) |
| `POST` | `/api/prescriptions/` | 201 | Создать назначение |
| `GET` | `/api/prescriptions/{id}/` | 200 | Получить одно назначение |
| `PUT` | `/api/prescriptions/{id}/` | 200 | Полностью заменить назначение |
| `DELETE` | `/api/prescriptions/{id}/` | 204 | Удалить назначение (архивируется в `deleted.jsonl` с полем `deleted_at`) |

### Тело запроса

**POST** — все поля необязательны:

```json
{
  "start_date": "2026-03-02",
  "medicines": [
    {
      "name": "Препарат А",
      "num_pills": 90,
      "per_day": 1,
      "pick_ups": [{"date": "2026-03-05", "num_pills": 90}]
    }
  ]
}
```

**PUT** — `start_date` и `medicines` обязательны, формат тот же.

| Поле | Тип | Ограничения |
|------|-----|-------------|
| `start_date` | date | в POST по умолчанию — сегодня |
| `medicines[].name` | string | непустое (пробелы по краям обрезаются) |
| `medicines[].num_pills` | int \| null | ≥ 1, необязательное |
| `medicines[].per_day` | float \| null | > 0, необязательное |
| `medicines[].pick_ups[]` | list | `{date: date, num_pills: int ≥ 1}`, оба поля обязательны |

Неизвестные и вычисляемые поля в запросе (`id`, `end_date`, `depletion_date`, `next_date`, `next_pick_up_date`, `next_date` у pick_up) **игнорируются** — сервер пересчитывает их сам. `id` при PUT не изменяется.

### Вычисляемые поля ответа

Расчёт выполняется, только если у препарата заданы `per_day` **и** хотя бы один `pick_up`; иначе соответствующие поля — `null`. Дни запаса: `ceil(таблетки / per_day)` (минимум 1), отсчёт от даты первого получения.

| Поле | Формула |
|------|---------|
| `pick_ups[].next_date` | дата, когда заканчивается накопленный запас − 7 дней |
| `depletion_date` | дата окончания всего запаса препарата |
| `next_pick_up_date` | `depletion_date` − 7 дней |
| `end_date` | минимум `depletion_date` по всем препаратам |
| `next_date` | `end_date` − 14 дней (дата нового визита к врачу) |

В ответе у препарата опускаются ключи `num_pills`/`per_day`, если они `null`; целочисленный `per_day` выводится как `1`, а не `1.0`. `pick_ups` сортируются по дате.

## Примеры ответов

**GET `/api/prescriptions/1/` → 200**

```json
{
  "id": 1,
  "start_date": "2026-03-02",
  "end_date": "2026-05-03",
  "next_date": "2026-04-19",
  "medicines": [
    {
      "name": "Препарат А",
      "num_pills": 90,
      "per_day": 1,
      "depletion_date": "2026-06-02",
      "next_pick_up_date": "2026-05-26",
      "pick_ups": [
        {"date": "2026-03-05", "next_date": "2026-05-26", "num_pills": 90}
      ]
    },
    {
      "name": "Препарат Б",
      "num_pills": 120,
      "per_day": 2,
      "depletion_date": "2026-05-03",
      "next_pick_up_date": "2026-04-26",
      "pick_ups": [
        {"date": "2026-03-05", "next_date": "2026-03-27", "num_pills": 60},
        {"date": "2026-04-03", "next_date": "2026-04-26", "num_pills": 60}
      ]
    }
  ]
}
```

**POST `/api/prescriptions/` с телом `{}` → 201**

```json
{
  "id": 1,
  "start_date": "2026-11-09",
  "end_date": null,
  "next_date": null,
  "medicines": []
}
```

**DELETE `/api/prescriptions/1/` → 204** — пустое тело.

## Ошибки

Все ошибки возвращаются в виде `{"detail": ...}`.

| Код | Когда | Пример тела |
|-----|-------|-------------|
| 400 | Ошибка валидации тела запроса или пути (например, нецелочисленный `id`, пустое `name`, `per_day ≤ 0`, неверный формат даты) | `{"detail": [{"type": "date_parsing", "loc": ["body", "start_date"], "msg": "Input should be a valid date...", "input": "02.03.2026"}]}` |
| 404 | Назначение с таким `id` не найдено (в т.ч. повторный DELETE) | `{"detail": "prescription 42 not found"}` |
| 500 | Файл хранилища повреждён (строка не является валидным JSON) | `{"detail": "/…/data/prescriptions.jsonl: malformed NDJSON on line 1"}` |

## Особенности хранилища

- Запись атомарная: файл перезаписывается через временный (`os.replace`).
- `id` последовательные и никогда не переиспользуются после удаления.
- При дублирующихся `id` в файле побеждает последняя запись.
- Доступ к файлам сериализуется блокировкой (`threading.RLock`).
