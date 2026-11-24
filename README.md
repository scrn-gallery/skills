# Скиллы Screen Gallery

Скиллы для ИИ-агентов — Codex, Claude и других. Работают с каталогом реальных сценариев мобильных приложений [Screen Gallery](https://scrn.gallery).

| Скилл | Что делает |
|---|---|
| [scrn-flow-compare](skills/scrn-flow-compare) | Сравнивает сценарии: одно приложение в разных версиях, несколько приложений на одной задаче или срез рынка. Результат — отчёт в чате, PDF, страницы картинками или карусель |

Нужна подписка Screen Gallery.

## Быстрая установка — для любого агента

Скопируйте и отправьте своему агенту (Codex, Claude Code, Cursor…):

```
Установи скилл scrn-flow-compare из https://github.com/scrn-gallery/skills и подключи MCP-сервер Screen Gallery https://scrn.gallery/mcp
```

Агент сам скачает скилл и пропишет сервер. Когда откроется браузер — войдите в аккаунт Screen Gallery. Потом перезапустите агента.

## Пошагово

### Codex — приложение, CLI, IDE
В терминале:
```
codex mcp add scrn --url https://scrn.gallery/mcp
codex mcp login scrn
npx skills add scrn-gallery/skills --skill scrn-flow-compare -a codex
```
Первая команда подключает Screen Gallery, вторая открывает вход в аккаунт, третья ставит скилл в `~/.codex/skills/`. Перезапустите Codex.

### Claude Code
```
claude mcp add --transport http scrn https://scrn.gallery/mcp
```
Затем в самом Claude Code:
```
/plugin marketplace add scrn-gallery/skills
/plugin install scrn-flow-compare@screen-gallery
```

### Cursor, Gemini CLI и другие
```
npx skills add scrn-gallery/skills --skill scrn-flow-compare
```
Установщик сам спросит, в какого агента положить скилл. MCP-сервер `https://scrn.gallery/mcp` подключается в настройках MCP вашего агента.

### claude.ai и Claude Desktop — без терминала
1. Подключите Screen Gallery в настройках коннекторов.
2. [Скачайте scrn-flow-compare.zip](https://github.com/scrn-gallery/skills/releases/latest/download/scrn-flow-compare.zip) и загрузите в настройках, в разделе навыков (skills).

Зелёная кнопка «Code» → «Download ZIP» скачивает весь проект: скилл там лежит глубоко внутри, и Claude его не найдёт. Нужен именно файл по ссылке выше.

## Как пользоваться
Опишите задачу словами:

> Найди в Screen Gallery все сценарии с рецептами у доставок продуктов. Сравни по шагам, у кого какая фишка, и собери PDF.

Дальше правьте как с дизайнером: «убери цены», «покажи кнопку в кадре», «переделай вывод».

Для PDF и картинок агенту нужен Python с Pillow (и reportlab для PDF) и доступ к scrn.gallery — агенты с терминалом обычно справляются сами. Без кода получится отчёт в чате.

## Лицензия
Код — MIT. Шрифт Inter — SIL Open Font License (`assets/fonts/OFL.txt`). Экраны приложений принадлежат их владельцам и берутся из каталога Screen Gallery по подписке.
