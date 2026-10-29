# Технический аудит и анализ репозитория Investing Demo

## 1. Назначение приложения и технологический стек (Задание №1)

### 1.1 Общее назначение и предметная область

Приложение **Investing Demo** — веб-сервис для учёта и мониторинга котировок акций на фондовом рынке. Предметная область:

- хранение справочника акций (тикер, FIGI, ISIN, название, валюта, внутренний идентификатор инструмента);
- отслеживание текущей цены инструмента и направления тренда (растёт / не растёт);
- визуализация исторических котировок в виде графика (последние 180 дней) через библиотеку Plotly;
- получение рыночных данных через публичное API **Tinkoff Invest** (клиент `tinkoff.invest`);
- аутентификация и регистрация пользователей (вход по email, выход);
- REST API для работы со списком акций (CRUD, фильтрация, поиск, сортировка);
- фоновое периодическое обновление цен акций через **Celery** + **Celery Beat** с брокером **Redis**;
- команда `add_shares` для первичной загрузки справочника инструментов из Tinkoff Invest в базу данных.

Целевая аудитория — инвесторы и трейдеры, которым требуется простой личный кабинет для отслеживания выбранных акций.

### 1.2 Версии базового стека

| Компонент | Версия / значение | Источник |
|-----------|-------------------|----------|
| Язык программирования | Python (конкретная версия не зафиксирована в репозитории) | — |
| Web-фреймворк | **Django 4.1.7** | `requirements.txt` (строка 13) |
| СУБД по умолчанию | **PostgreSQL** (`django.db.backends.postgresql`) | `config/settings.py` (строки 91–104) |
| Имя БД | `investing` | `config/settings.py`, строка 98 |
| Пользователь БД | `postgres` / пароль `postgres` (хардкод) | `config/settings.py`, строки 99–100 |
| Хост БД | `localhost:5432` | `config/settings.py`, строки 101–102 |
| Брокер сообщений Celery | Redis `redis://127.0.0.1:6379/0` | `config/settings.py`, строка 141 |
| ASGI / WSGI | `django.core.asgi.get_asgi_application` / `django.core.wsgi.get_wsgi_application` | `config/asgi.py`, `config/wsgi.py` |

Примечание: Django 4.1.7 на момент аудита уже не получает регулярных обновлений безопасности (вышла из активной поддержки), что считается устаревшим стеком (см. раздел 5).

### 1.3 Внешние библиотеки и зависимости (requirements.txt) — часть 1

Ниже приведён детальный разбор библиотек из `requirements.txt` с указанием назначения каждой в контексте проекта.

| № | Пакет | Версия | Назначение в проекте |
|---|-------|--------|----------------------|
| 1 | `amqp` | 5.1.1 | Библиотека протокола AMQP, используется Kombu/Celery для взаимодействия с брокером сообщений. |
| 2 | `asgiref` | 3.6.0 | ASGI-совместимость; зависимость Django для работы WSGI/ASGI серверов. |
| 3 | `async-timeout` | 4.0.2 | Таймауты для асинхронного кода; зависимость celery/redis. |
| 4 | `billiard` | 3.6.4.0 | Форк multiprocessing, используется Celery для параллельной обработки задач. |
| 5 | `black` | 23.1.0 | Автоматический форматтер кода Python (инструмент разработки). |
| 6 | `cachetools` | 5.3.0 | Инструменты кэширования. |
| 7 | `celery` | 5.2.7 | Распределённая очередь задач; фоновое обновление цен акций и Celery Beat. |
| 8 | `click` | 8.1.3 | CLI-фреймворк; зависимость Celery. |
| 9 | `click-didyoumean` | 0.3.0 | Подсказки Click при опечатках команд. |
| 10 | `click-plugins` | 1.1.1 | Поддержка плагинов Click. |
| 11 | `click-repl` | 0.2.0 | Интерактивная оболочка для Click-приложений. |
| 12 | `crispy-bootstrap3` | 2022.1 | Интеграция django-crispy-forms с Bootstrap 3. |
| 13 | `Django` | 4.1.7 | Основной веб-фреймворк (ORM, MVT, админ-панель, аутентификация). |
| 14 | `django-crispy-forms` | 2.0 | Рендеринг форм Django с красивым оформлением (`as_crispy_field`). |
| 15 | `django-filter` | 22.1 | Фильтрация queryset’ов; используется в REST API (`ShareFilter`, `DjangoFilterBackend`). |
| 16 | `djangorestframework` | 3.14.0 | REST API (`ShareViewSet`, `ShareSerializer`, сериализация модели `Share`). |
| 17 | `grpcio` | 1.51.3 | gRPC; прямая зависимость клиента Tinkoff Invest API. |
| 18 | `isort` | 5.12.0 | Инструмент сортировки импортов Python (разработка). |
| 19 | `kombu` | 5.2.4 | Библиотека обмена сообщениями, транспортный слой Celery. |
| 20 | `mypy-extensions` | 1.0.0 | Расширения для статического анализатора mypy (разработка). |
| 21 | `packaging` | 23.0 | Утилиты для работы с версиями пакетов (разработка/инструменты). |
| 22 | `pathspec` | 0.11.1 | Совместимость с `.gitignore`; зависимость инструментов форматирования. |
| 23 | `platformdirs` | 3.1.1 | Определение системных директорий (разработка). |
| 24 | `plotly` | 5.13.1 | Построение интерактивных графиков; используется в `dashboard/services/graph.py`. |
| 25 | `prompt-toolkit` | 3.0.38 | Интерактивные интерфейсы командной строки (зависимость `click-repl`). |
| 26 | `protobuf` | 3.20.3 | Протоколы сериализации gRPC; зависимость `grpcio` и клиента Tinkoff. |
| 27 | `psycopg2-binary` | 2.9.5 | Адаптер PostgreSQL для Python; драйвер подключения Django к БД. |
| 28 | `pydantic` | 1.10.6 | Валидация данных; версия 1.x (устарелая). |
| 29 | `python-dateutil` | 2.8.2 | Работа с датами и временем; зависимость Tinkoff/Plotly. |
| 30 | `pytz` | 2022.7.1 | Часовые пояса; зависимость Django/celery. |
| 31 | `redis` | 4.5.1 | Клиент Redis; брокер Celery. |
| 32 | `six` | 1.16.0 | Совместимость Python 2/3 (устаревшая зависимость). |
| 33 | `sqlparse` | 0.4.3 | Парсинг SQL; зависимость Django Debug Toolbar/форматирования. |
| 34 | `tenacity` | 8.2.2 | Библиотека повторов (retry); зависимость клиента Tinkoff. |
| 35 | `tinkoff` | 0.1.1 | Клиент Tinkoff Invest API (старый/альтернативный пакет). |
| 36 | `tinkoff-investments` | 0.2.0b50 | Основной клиент Tinkoff Invest API (бета-версия); используется в `graph.py`, `market_data.py`, `add_shares.py`. |
| 37 | `tomli` | 2.0.1 | Парсер TOML (зависимость инструментов разработки). |
| 38 | `typing_extensions` | 4.5.0 | Бэкпорты типизации (зависимость pydantic/mypy). |
| 39 | `vine` | 5.0.0 | Абстракция промиса/обещаний; зависимость Celery/Kombu. |
| 40 | `wcwidth` | 0.2.6 | Ширина символов в терминале (зависимость prompt-toolkit). |

**Критические замечания по зависимостям:**
- Django 4.1.7 уже не находится в активной поддержке (требуется миграция на поддерживаемую версию, например Django 4.2 LTS или 5.x).
- `tinkoff-investments` — бета-версия `0.2.0b50`, API может быть нестабильным.
- `pydantic` 1.10.6 — версия первого поколения (v1), отсутствует поддержка pydantic v2.
- Значительное количество пакетов зафиксировано без семантических диапазонов (точные `==` версии), что затрудняет автоматическое обновление.

## 2. Структура проекта и архитектура

### 2.1 Дерево каталогов проекта (краткое)

```
investing-cline/
├── .gitignore, docker-compose.yml, HOMEWORK.md, manage.py, README.md, requirements.txt, ANALYSIS.md
├── config/        (asgi.py, celery.py, settings.py, urls.py, wsgi.py)
├── dashboard/     (admin.py, apps.py, forms.py, models.py, tasks.py, tests.py, urls.py, views.py)
│   ├── api/v1/    (router.py, serializer.py, urls.py, views.py)
│   ├── management/commands/add_shares.py
│   ├── migrations/ (0001 … 0007)
│   ├── services/  (graph.py, market_data.py)
│   ├── static/dashboard/css/
│   └── templates/dashboard/ (base, list, detail, create, delete)
└── user/          (apps.py, forms.py, models.py, urls.py, views.py)
    ├── migrations/
    └── templates/user/ (base, auth, registration)
```

### 2.2 Архитектурный паттерн (MVT) и схема взаимодействия компонентов

Проект следует классическому паттерну **MVT (Model-View-Template)**, характерному для Django:

1. **Маршрутизация запросов (`urls.py`)** — входящий HTTP-запрос попадает в корневой диспетчер `config/urls.py`, который распределяет его между：
   - `admin/` — встроенная админ-панель Django;
   - `` (пустой префикс) — `dashboard.urls` — веб-интерфейс (`/`, `/<int:pk>`, `/create`, `/update/<int:pk>`, `/delete/<int:pk>`, `/api/...`);
   - `user` — `user.urls` — аутентификация (`/login/`, `/registration/`, `/logout/`).
   Внутри `dashboard/urls.py` дополнительно подключается `dashboard.api.urls` → `dashboard.api.v1.urls` → DRF `DefaultRouter`, регистрирующий `ShareViewSet` по адресу `/api/v1/shares/`.

2. **Обработка логики (`views.py`)** — представления реализованы как классовые (CBV):
   - `dashboard/views.py`: `ShareListView` (ListView), `ShareDetailView` (View), `ShareCreateView` (CreateView), `ShareUpdateView` (UpdateView), `ShareDeleteView` (DeleteView), миксин `IsUserAuthenticatedMixin`;
   - `user/views.py`: `AuthView`, `RegistrationView`, `LogoutView`;
   - `dashboard/api/v1/views.py`: `ShareViewSet` (ModelViewSet) для REST API.

3. **Представление данных (`templates/`)** — шаблоны Django загружаются через `APP_DIRS = True` (каждый приложение хранит шаблоны в `templates/<app_name>/`). Используется наследование шаблонов (`{% extends %}`), блоки (`{% block %}`), теги CSRF, url и static, фильтры crispy-forms.

4. **Взаимодействие с базой данных (Django ORM)** — модель `Share` в `dashboard/models.py` абстрагирует таблицу БД. ORM используется в представлениях (`Share.objects.all()`, `.get()`, `.filter().update()`), в REST API (`queryset = Share.objects.all()`), в Celery-задаче и в管理命令 (`Share.objects.get_or_create(...)`).

**Схема взаимодействия (текстовая):**

```
Пользователь / API-клиент
        │
        ▼
[config/urls.py] ──┬── admin/ → admin.site.urls
                   ├─ ''      → dashboard/urls.py → dashboard/views.py (Share*View)
                   └─ 'user'  → user/urls.py      → user/views.py (Auth/Reg/Logout)

dashboard/urls.py ──┬─ ''          → ShareListView   (dashboard/templates/dashboard/list.html)
                    ├─ '<int:pk>'  → ShareDetailView (dashboard/services/graph.py → Plotly)
                    ├─ 'create'    → ShareCreateView (ShareModelForm)
                    ├─ 'update/<pk>' → ShareUpdateView (ShareModelForm)
                    ├─ 'delete/<pk>' → ShareDeleteView
                    └─ 'api/'      → dashboard/api/urls → dashboard/api/v1/urls → DRF DefaultRouter
                                                                            → ShareViewSet → ORM → PostgreSQL

Celery Beat ──→ Celery Worker ──→ dashboard/tasks.update_last_price ──→ Tinkoff API → ORM (обновление цен)
Управляющая команда add_shares ──→ Tinkoff API ──→ ORM (заполнение справочника акций)
```

## 3. Модель данных (Сущности и связи)

### 3.1 Сущность Share (dashboard/models.py)

Единственная бизнес-сущность в приложении — **акция** (`Share`):

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | `BigAutoField` | `primary_key=True`, автоинкремент | Внутренний идентификатор записи |
| `figi` | `CharField(255)` | `unique=True` | FIGI инструмента (уникальный идентификатор Tinkoff) |
| `isin` | `CharField(255)` | — | ISIN код инструмента |
| `name` | `CharField(255)` | `verbose_name="Наименование компании"` | Название эмитента |
| `ticker` | `CharField(10)` | `unique=True`, `verbose_name="Тикер"` | Тикер акции |
| `currency` | `CharField(20)` | `verbose_name="Валюта"` | Валюта котировки |
| `uid` | `CharField(255)` | `unique=True` | Внутренний uid инструмента Tinkoff |
| `last_price` | `FloatField` | `blank=True, null=True`, `verbose_name="Текущая цена"` | Последняя известная цена |
| `is_trend_high` | `BooleanField` | `blank=True, null=True`, `verbose_name="Растет цена"` | Флаг направления тренда |
| `updated_at` | `DateTimeField` | `auto_now=True`, `blank=True, null=True` | Время последнего обновления цены |

**Мета-данные:** `verbose_name = "Акция"`, `verbose_name_plural = "Акции"`.

### 3.2 Сущность Пользователь

Приложение не определяет собственную модель пользователя. В `user/models.py` импортируется стандартная модель Django:

```python
from django.contrib.auth import get_user_model
User = get_user_model()
```

То есть используется стандартная `django.contrib.auth.models.User` (поле `username`, которое в представлениях используется как email). Пароли хранятся хешированными средствами Django (`create_user`).

### 3.3 Связи сущностей

**Явных связей (`ForeignKey`, `OneToOneField`, `ManyToManyField`) между моделями нет.** `Share` — независимая сущность, пользователи не привязаны к конкретным акциям на уровне БД (нет модели избранного, портфеля, транзакций).

### 3.4 Текстовая схема связей (Mermaid)

```mermaid
erDiagram
    Share ||--o{ Share : "самостоятельная сущность (нет связей)"
    Share {
        bigserial id PK
        varchar figi UK
        varchar isin
        varchar name
        varchar ticker UK
        varchar currency
        varchar uid UK
        float8 last_price NULL
        boolean is_trend_high NULL
        timestamp updated_at NULL
    }
    User ||--o{ Share : "нет прямой связи (только через сессии Django)"
```

### 3.5 История миграций (dashboard/migrations)

Всего 7 миграций, generated Django 4.1.7:

1. `0001_add_share.py` — создание модели `Share` с полями `id`, `figi`, `isin`, `name`, `ticker`, `currency` (без уникальности);
2. `0002_update_share.py` — добавление `unique=True` для `figi` и `ticker`;
3. `0003_add_uuid.py` — добавление поля `uid` со значением по умолчанию `''` (`preserve_default=False`);
4. `0004_add_last_price.py` — добавление `is_trend_high`, `last_price`, изменение `verbose_name` для `currency`, `name`, `ticker` (в миграции допущены опечатки: `name` получил `verbose_name="Валюта"`, `ticker` — `"Ти"`);
5. `0005_add_verbose_name.py` — исправление `verbose_name` у `name` на `"Наименование компании"`;
6. `0006_add_verbose_name.py` — исправление `verbose_name` у `ticker` на `"Тикер"`;
7. `0007_add_updated_at.py` — добавление поля `updated_at` с `auto_now=True`.

**Замечание:** фрагментированная и частично ошибочная история миграций требует очистки (см. раздел 5).

## 4. Восстановленные функциональные требования (Задание №2)

Ниже приведён нумерованный список функциональных требований, строго Recovery из исходного кода. Для каждого требования указано поведение, подтверждение в коде и правила валидации.

### ФТ-1. Просмотр списка акций (веб-интерфейс)

- **Поведение:** Пользователь открывает главную страницу и видит таблицу акций с колонками: Тикер, Название, ISIN, Текущая цена (с цветовой индикацией тренда: зелёный — растёт, красный — не растёт), Управление (для авторизованных). Реализована пагинация по 100 записей, сортировка по имени. Если акций нет — выводится сообщение «Акций еще нет».
- **Подтверждение в коде:** `dashboard/views.py` — `ShareListView(ListView)` (`model = Share`, `paginate_by = 100`, `ordering = ["name"]`); `dashboard/urls.py` — `path("", ShareListView.as_view(), name="index")`; `dashboard/templates/dashboard/list.html`.
- **Модели:** `Share`.
- **Валидация/ограничения:** Доступ к кнопкам создания/редактирования/удаления ограничен проверкой `user.is_authenticated` в шаблоне. Пагинация фиксирована на 100 записей на страницу.

### ФТ-2. Просмотр детальной информации об акции с графиком

- **Поведение:** При переходе на страницу акции (`/<int:pk>/`) отображается название, текущая цена и валюта, время последнего обновления, а также интерактивный график исторических котировок за последние 180 дней (построен через Plotly, источник — Tinkoff Invest API, интервал дневных свечей).
- **Подтверждение в коде:** `dashboard/views.py` — `ShareDetailView(View).get(request, pk)`; `dashboard/services/graph.py` — функция `get_graph(share)` (запрос `client.get_all_candles(figi=..., from_=now()-timedelta(days=180), interval=CandleInterval.CANDLE_INTERVAL_DAY)`); `dashboard/urls.py` — `path("<int:pk>", ShareDetailView.as_view(), name="detail")`; `dashboard/templates/dashboard/detail.html`.
- **Модели:** `Share` (поле `figi` используется для запроса к API).
- **Валидация/ограничения:** При отсутствии акции с переданным `pk` `Share.objects.get(id=pk)` вызовет `DoesNotExist` → HTTP 500 вместо 404 (отсутствует обработка 404). График строится только при наличии валидного `TINKOFF_TOKEN` и доступа к API.

### ФТ-3. Создание новой записи об акции (веб-форму)

- **Поведение:** Авторизованный пользователь может добавить новую акцию через форму на странице `/create`. После успешного сохранения происходит редирект на главную страницу.
- **Подтверждение в коде:** `dashboard/views.py` — `ShareCreateView(IsUserAuthenticatedMixin, CreateView)` (`form_class = ShareModelForm`, `template_name = "dashboard/create.html"`, `success_url = reverse_lazy("dashboard:index")`); `dashboard/forms.py` — `ShareModelForm(ModelForm)` (`fields = "__all__"`); `dashboard/urls.py` — `path("create", ShareCreateView.as_view(), name="create")`; `dashboard/templates/dashboard/create.html`.
- **Модели:** `Share`.
- **Валидация/ограничения:** Доступ ограничен миксином `IsUserAuthenticatedMixin` (проверка `request.user.is_authenticated`, иначе редирект на `dashboard:index`). Форма использует все поля модели, включая уникальные `figi`, `ticker`, `uid` — при дублировании сработает валидация уникальности на уровне БД/формы.

### ФТ-4. Редактирование существующей акции (веб-форму)

- **Поведение:** Авторизованный пользователь может отредактировать поля акции на странице `/update/<int:pk>/`. После сохранения — редирект на главную.
- **Подтверждение в коде:** `dashboard/views.py` — `ShareUpdateView(IsUserAuthenticatedMixin, UpdateView)` (`model = Share`, `form_class = ShareModelForm`, `success_url = reverse_lazy("dashboard:index")`); `dashboard/urls.py` — `path("update/<int:pk>", ShareUpdateView.as_view(), name="update")`.
- **Модели:** `Share`.
- **Валидация/ограничения:** Доступ ограничен `IsUserAuthenticatedMixin`. Редактируются все поля модели (`fields = "__all__"`), включая уникальные identifiers.

### ФТ-5. Удаление акции

- **Поведение:** Авторизованный пользователь может удалить акцию через страницу подтверждения `/delete/<int:pk>/`. После удаления — редирект на главную.
- **Подтверждение в коде:** `dashboard/views.py` — `ShareDeleteView(IsUserAuthenticatedMixin, DeleteView)` (`model = Share`, `template_name = "dashboard/delete.html"`, `success_url = reverse_lazy("dashboard:index")`); `dashboard/urls.py` — `path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete")`; `dashboard/templates/dashboard/delete.html`.
- **Модели:** `Share`.
- **Валидация/ограничения:** Доступ ограничен `IsUserAuthenticatedMixin`. Защита от случайного удаления реализована только через страницу подтверждения (GET — форма, POST — удаление).

### ФТ-6. Регистрация нового пользователя

- **Поведение:** Новый пользователь заполняет форму регистрации (email, пароль, подтверждение пароля). При успешной валидации создаётся учётная запись, выполняется автоматический вход и редирект на главную. При ошибке отображается сообщение об ошибке.
- **Подтверждение в коде:** `user/views.py` — `RegistrationView(View)`; `user/forms.py` — `RegistrationForm(forms.Form)`; `user/urls.py` — `path("registration/", RegistrationView.as_view(), name="registration")`; `user/templates/user/registration.html`.
- **Модели:** стандартная `User` (через `get_user_model()`).
- **Валидация/ограничения:**
  - Поля `email`, `password1`, `password2` обязательны (`required=True`).
  - `email` — `EmailField` (проверка формата email).
  - В `clean()` проверяется совпадение `password1` и `password2` («Введенные пароли не совпадают»).
  - Проверяется уникальность email через `User.objects.filter(email=email)` («Данный e-mail уже зарегистрирован!»).
  - `save()` создаёт пользователя через `User.objects.create_user(email, email, password)` (email используется как username и email) и выполняет `authenticate`.

### ФТ-7. Аутентификация пользователя (вход)

- **Поведение:** Пользователь вводит email и пароль на странице `/login/`. При успешной аутентификации выполняется `login` и редирект на главную. При неудаче — отображается ошибка «Неверный логин или пароль! Повторите попытку».
- **Подтверждение в коде:** `user/views.py` — `AuthView(View)`; `user/forms.py` — `AuthForm(forms.Form)`; `user/urls.py` — `path("login/", AuthView.as_view(), name="auth")`; `user/templates/user/auth.html`.
- **Модели:** стандартная `User`.
- **Валидация/ограничения:** Поля `email` и `password` обязательны. В `post` используется `form.data["email"].lower()` (приведение к нижнему регистру) и `authenticate(request, username=..., password=...)`. **Дефект:** используется `form.data` вместо `form.cleaned_data` (см. раздел 5).

### ФТ-8. Выход пользователя (logout)

- **Поведение:** Авторизованный пользователь может выйти из системы по кнопке «Выход» (`/logout/`), после чего выполняется `logout` и редирект на главную.
- **Подтверждение в коде:** `user/views.py` — `LogoutView(View).get(request)`; `user/urls.py` — `path("logout/", LogoutView.as_view(), name="logout")`; ссылка в `dashboard/templates/dashboard/base.html` (`{% url 'user:logout' %}`).
- **Модели:** `django.contrib.auth` (сессия).
- **Валидация/ограничения:** Выход доступен по GET-запросу без дополнительной защиты (стандартное поведение Django, но с точки зрения безопасности предпочтительнее POST).

### ФТ-9. Импорт справочника акций из Tinkoff Invest

- **Поведение:** Команда管理 `python manage.py add_shares` подключается к Tinkoff Invest API, получает список всех акций (`client.instruments.shares()`) и создаёт записи в таблице `Share` с использованием `get_or_create` по `figi`.
- **Подтверждение в коде:** `dashboard/management/commands/add_shares.py` — класс `Command(BaseCommand)`; `README.md` — инструкция запуска.
- **Модели:** `Share`.
- **Валидация/ограничения:** Требуется непустой `TINKOFF_TOKEN` в `config/settings.py`. Дубликаты по `figi` обрабатываются через `get_or_create` (повторный запуск не создаёт дубликатов).

### ФТ-10. Фоновое обновление цен акций (Celery)

- **Поведение:** Периодическая задача Celery `update_last_price` обходит все акции, запрашивает текущую цену через `client.market_data.get_last_prices(figi=[...])`, определяет направление тренда (сравнение с предыдущей ценой) и обновляет поля `last_price` и `is_trend_high` в БД.
- **Подтверждение в коде:** `dashboard/tasks.py` — функция `update_last_price` с декоратором `@app.task`; `config/celery.py` — `app.conf.beat_schedule` с задачей `dashboard.tasks.update_last_price` и интервалом `10.0` (в комментарии указано «5 минут», но в коде 10 секунд); `config/settings.py` — настройки Celery (`CELERY_BROKER_URL`, `CELERY_TIMEZONE = "Europe/Moscow"`, `CELERY_TASK_TRACK_STARTED = True`).
- **Модели:** `Share`.
- **Валидация/ограничения:** Требуется запущенный Redis-брокер и Celery Worker/Beat. Требуется валидный `TINKOFF_TOKEN`. Ошибки при запросе к API или при сравнении цен логгируются и заглатываются (`try/except Exception`), выполнение задачи продолжается для остальных акций.

### ФТ-11. REST API акций

- **Поведение:** REST API по адресу `/api/v1/shares/` предоставляет полный набор операций CRUD над акциями (список, создание, чтение, обновление, удаление). Поддерживается фильтрация по `name` и `ticker`, поиск по `name`, сортировка по `name` и `ticker`. Пагинация — `LimitOffsetPagination` с размером страницы 100.
- **Подтверждение в коде:** `dashboard/api/v1/views.py` — `ShareViewSet(viewsets.ModelViewSet)`, `ShareFilter(filters.FilterSet)`; `dashboard/api/v1/serializer.py` — `ShareSerializer(ModelSerializer)`; `dashboard/api/v1/router.py` — регистрация `r"shares"`; `dashboard/api/v1/urls.py` + `dashboard/api/urls.py` + `dashboard/urls.py` — маршрутизация; `dashboard/tests.py` — тесты `DashboardTests(APITestCase)`.
- **Модели:** `Share`.
- **Валидация/ограничения:** Сериализатор включает поля `id`, `figi`, `isin`, `name`, `ticker`, `currency`, `last_price`, `is_trend_high`, `updated_at`. Уникальность `figi` и `ticker` контролируется на уровне модели/БД. **Дефект:** класс `ShareViewSet` не имеет явных классов доступа (`permission_classes`), поэтому по умолчанию DRF может разрешать неаутентифицированный доступ в зависимости от глобальных настроек (в `settings.py` `DEFAULT_PERMISSION_CLASSES` не переопределен).

## 5. Выявленные технические проблемы, дефекты и устаревшие решения

### 5.1 Устаревшие зависимости и синтаксис Django

| Проблема | Детали | Риск |
|----------|--------|------|
| **Django 4.1.7** | Версия вышедшая из активной поддержки (EOL). Отсутствуют патчи безопасности для новых уязвимостей. | Уязвимости безопасности, отсутствие совместимости с новыми версиями Python и библиотек. |
| **`tinkoff-investments==0.2.0b50`** | Бета-версия клиента Tinkoff Invest API. API может меняться без обратной совместимости. | Риск разрыва интеграции при обновлении пакета или изменении стороннего API. |
| **`pydantic==1.10.6`** | Поколение v1, уступает v2 по производительности и функционалу. | Устаревший стек валидации, потенциальные конфликты с другими пакетами. |
| **`async-timeout==4.0.2`, `six==1.16.0`** | Устаревшие вспомогательные пакеты. | Технический долг, потенциальные проблемы совместимости. |
| **Точные версии `==` без диапазонов** | Все зависимости зафиксированы жёстко. | Сложность автоматического обновления, риск конфликтов зависимостей при установке. |

### 5.2 Ошибки конфигурации и безопасности

1. **Пустой `SECRET_KEY`** (`config/settings.py`, строка 6) — критическая уязвимость: механизмы защиты CSRF, подписи сессий и сброса паролей не работают корректно.
2. **`DEBUG = True`** (строка 8) в сочетании с пустым `ALLOWED_HOSTS = []` (строка 10) — недопустимо для production: при ошибке будет раскрыта отладочная информация, а запрос с любым хостом будет отклонён.
3. **Хардкод учётных данных БД** (`postgres` / `postgres`) в `settings.py` — нарушение принципа хранения секретов вне кода (должно использоваться `.env` / переменные окружения).
4. **Пустой `TINKOFF_TOKEN`** (строка 134) — все функции, dépendent от Tinkoff API (график, текущая цена, импорт акций), не будут работать без ручного заполнения токена.
5. **Отсутствие `.env.example`** — нет шаблона обязательных переменных окружения для развёртывания.
6. **Монтирование всего репозитория в контейнер** (`docker-compose.yml`, строка 14: `./:/app`) — потенциальная утечка исходного кода и секретов в контейнер БД.

### 5.3 Дефекты реализации и потенциальные ошибки выполнения

| # | Дефект | Место | Последствия |
|---|--------|-------|-------------|
| 1 | `Share.objects.get(id=pk)` без `get_object_or_404` | `dashboard/views.py`, `ShareDetailView.get` | При отсутствии акции с указанным `pk` вызывается `DoesNotExist` → HTTP 500 вместо 404. |
| 2 | `AuthForm` передаётся в шаблон как **класс**, а не экземпляр | `user/views.py`, `AuthView.get`: `{"form": AuthForm}` | Поля формы не отрендерены корректно (отсутствуют связанные данные, ошибки валидации). |
| 3 | Использование `form.data["email"]` вместо `form.cleaned_data` | `user/views.py`, `AuthView.post` | Если форма не валидна, возникнет `KeyError`; обходит очищенные/нормализованные данные. |
| 4 | `form.errors["__all__"].data[0].message` | `user/views.py`, `RegistrationView.post` | Если ошибок нет или структура отличается — `IndexError` / `AttributeError`. |
| 5 | `resp.last_prices.pop()` без проверки пустоты | `dashboard/services/market_data.py`, `get_last_data` | При пустом списке цен от API — `IndexError`, падение задачи Celery. |
| 6 | Сравнение `share.last_price > last_price` при `None` | `dashboard/tasks.py`, `update_last_price` | `TypeError` при первом обновлении (цена `None`); исключение заглатывается, тренд принудительно ставится `True`. |
| 7 | Только `.units` цены, игнорируются `.nano` | `dashboard/services/market_data.py` | Потеря точности цены (дробная часть отбрасывается). |
| 8 | Опечатка имени переменной `detetime` | `dashboard/tasks.py`, строка 13 | Нарушение читаемости кода (переменная не используется дальше, но указывает на низкое качество). |
| 9 | `enctype="multipart/form-data"` в форме без файлов | `dashboard/templates/dashboard/create.html`, строка 13 | Некоректный тип кодирования формы для обычных текстовых полей. |

### 5.4 Дефекты верстки и шаблонов

1. **Невалидные CSS-классы:** в `detail.html` и `list.html` используются классы `col3` вместо `col-3` (Bootstrap), что ломает сетку.
2. **Незакрытые теги `<td>`:** в `list.html` (строки 36–40) при conditional-открытии `<td style="...">` второй тег `<td>` не закрывает первый, что порождает Invalid HTML.
3. **`{% autoescape off %}` для `plot_div`:** в `detail.html` вывод HTML-графика без экранирования — потенциальная XSS-уязвимость, если данные из Plotly когда-либо будут содержать пользовательский ввод.
4. **Шаблон `user/base.html` подключает собственную статику Bootstrap** (`user/css/bootstrap.min.css`, `user/css/signin.css`), но эти файлы отсутствуют в репозитории (в папке `user/static` ничего нет) — страницы авторизации/регистрации будут без оформления.

### 5.5 Архитектурные антипаттерны и дублирование

1. **Отсутствие разграничения прав доступа в REST API:** `ShareViewSet` не имеет `permission_classes` (например, `IsAuthenticated`), поэтому API может быть доступен неавторизованным пользователям, в то время как веб-представления защищены `IsUserAuthenticatedMixin`.
2. **Дублирование шаблона формы:** `ShareCreateView` и `ShareUpdateView` используют один и тот же шаблон `dashboard/create.html`, но для удаления выделен отдельный шаблон — логично, но форма редактирования не отличается от формы создания визуально.
3. **Тонкие модели, толстые сервисы/представления:** бизнес-логика определения тренда и сравнения цен размазана по `tasks.py` и `views.py`, модель `Share` не содержит методов доменной логики (например, `update_price`).
4. **Избыточная история миграций:** 7 миграций для одной модели с несколькими исправлениями опечаток (`0004` → `0005` → `0006`) указывают на отсутствие squash-миграций и аккуратного первоначального проектирования.
5. **`FloatField` для денежных значений:** `last_price` и цены из Tinkoff хранятся в `FloatField`, что неприемлемо для финансовых расчётов из-за проблем с плавающей точкой (рекомендуется `DecimalField`).
6. **Celery Beat интервал не соответствует описанию:** в `config/celery.py` задача `add-every-5-min` запускается каждые **10.0 секунд**, а не 5 минут, что приведёт к избыточным запросам к Tinkoff API и возможным ограничениям по rate limit.

### 5.6 Тестирование и качество кода

- Тесты покрывают только REST API (`dashboard/tests.py`, `APITestCase`); нет тестов для веб-представлений, форм, Celery-задач, сервисов.
- Отсутствуют линтеры/статические анализаторы в CI (хотя в зависимостях присутствуют `black`, `isort`, `mypy`), что не гарантирует единообразия кода.

---

## Итог

Приложение **Investing Demo** реализует базовый функционал учёта и мониторинга акций с использованием Django MVT, DRF, Celery и Tinkoff Invest API. Код работоспособен в демонстрационном проекте, но содержит значительное количество критических и высоких дефектов: пустой `SECRET_KEY`, хардкод секретов, отсутствие обработки 404, потенциальные `KeyError`/`IndexError`/`TypeError` в runtime, отсутствие прав доступа в API, невалидная верстка и устаревший стек (Django 4.1.7, бета-клиент Tinkoff). Перед дальнейшей разработкой и выкладкой в production необходимо устранить проблемы раздела 5, обновить зависимости и привести конфигурацию к режиму production.






