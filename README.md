# dreamShare

Lightweight self-hosted service for fast file and text transfer between devices. Pair devices via QR code and exchange files, links, and code snippets in a private room — no accounts required.

## Features

- File upload via web UI (up to 10 GB per request)
- Instant shareable download links
- Text and link sharing between paired devices
- Code snippets with optional syntax highlighting (highlight.js)
- Delete messages for all participants (files erased from the server immediately)
- Device pairing via QR code; multiple devices can be bridged into one room
- Automatic cleanup: files, messages, and inactive rooms are removed after 24 hours
- Room state persists across restarts (`share_state.json`)
- SEO basics included: `robots.txt` and `sitemap.xml`

## Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)

## Setup

```bash
pip install -r requirements.txt
python app.py
```

The app listens on `0.0.0.0:5028`. Uploaded files are stored in the local `uploads/` directory (created automatically) and deleted automatically after 24 hours.

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/api/init/<node_id>` | GET | Register a device, get its room ID |
| `/api/push` | POST | Send text or upload a file |
| `/api/poll/<node_id>` | GET | Fetch new messages for a device |
| `/api/participants/<node_id>` | GET | List devices in the room |
| `/api/bridge` | POST | Merge multiple devices into one room |
| `/api/delete` | POST | Delete a message for everyone |
| `/api/cleanup` | POST | Trigger cleanup manually |
| `/download/<filename>` | GET | Download an uploaded file |

## Contact

Telegram: [@dreamcatch_r](https://t.me/dreamcatch_r)

---

# dreamShare (RU)

Лёгкий самостоятельно разворачиваемый сервис для быстрой передачи файлов
и текста между устройствами. Свяжите устройства по QR-коду и обменивайтесь
файлами, ссылками и фрагментами кода в приватной комнате — без регистрации.

## Возможности

- Загрузка файлов через веб-интерфейс (до 10 ГБ за запрос)
- Мгновенные публичные ссылки для скачивания
- Обмен текстом и ссылками между связанными устройствами
- Фрагменты кода с опциональной подсветкой синтаксиса (highlight.js)
- Удаление сообщений у всех участников (файлы сразу стираются с сервера)
- Связывание устройств по QR-коду; несколько устройств можно объединить в одну комнату
- Автоматическая очистка: файлы, сообщения и неактивные комнаты удаляются через 24 часа
- Состояние комнаты сохраняется между перезапусками (`share_state.json`)
- Базовое SEO: `robots.txt` и `sitemap.xml`

## Стек

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)

## Установка

```bash
pip install -r requirements.txt
python app.py
```

Приложение слушает `0.0.0.0:5028`. Загруженные файлы хранятся в локальном
каталоге `uploads/` (создаётся автоматически) и автоматически удаляются
через 24 часа.

## Обзор API

| Эндпоинт | Метод | Описание |
|---|---|---|
| `/api/init/<node_id>` | GET | Зарегистрировать устройство, получить ID комнаты |
| `/api/push` | POST | Отправить текст или загрузить файл |
| `/api/poll/<node_id>` | GET | Получить новые сообщения устройства |
| `/api/participants/<node_id>` | GET | Список устройств в комнате |
| `/api/bridge` | POST | Объединить несколько устройств в одну комнату |
| `/api/delete` | POST | Удалить сообщение у всех |
| `/api/cleanup` | POST | Запустить очистку вручную |
| `/download/<filename>` | GET | Скачать загруженный файл |

## Контакты

Telegram: [@dreamcatch_r](https://t.me/dreamcatch_r)
