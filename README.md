# Скиллы Screen Gallery

### ⬇️ [Скачать scrn-flow-compare.zip](https://github.com/scrn-gallery/skills/releases/latest/download/scrn-flow-compare.zip)

Это всё, что нужно для claude.ai: файл загружается в настройках, в разделе навыков (skills). Зелёная кнопка «Code» → «Download ZIP» скачивает весь проект — для загрузки в Claude она не подходит.

Скиллы для ИИ-агентов — Claude, Codex и других, кто понимает формат `SKILL.md`. Работают с каталогом реальных сценариев мобильных приложений [Screen Gallery](https://scrn.gallery).

| Скилл | Что делает |
|---|---|
| [scrn-flow-compare](skills/scrn-flow-compare) | Сравнивает сценарии: одно приложение в разных версиях, несколько приложений на одной задаче или срез рынка. Результат — отчёт в чате, PDF, страницы картинками или карусель |

## Что нужно
1. Подписка Screen Gallery и подключённый к агенту MCP-сервер Screen Gallery: `https://scrn.gallery/mcp`.
2. Агент, который умеет запускать код (Python 3 + Pillow, для PDF ещё reportlab). Без кода будет отчёт в чате.
3. Доступ из этой среды к scrn.gallery — оттуда скачиваются экраны.

## Установка

**Claude (claude.ai, десктоп).** [Скачайте scrn-flow-compare.zip](https://github.com/scrn-gallery/skills/releases/latest/download/scrn-flow-compare.zip) и загрузите в настройках, в разделе навыков (skills). Коннектор Screen Gallery подключается там же, в коннекторах.

**Claude Code**
```
claude mcp add --transport http scrn https://scrn.gallery/mcp
/plugin marketplace add scrn-gallery/skills
/plugin install scrn-flow-compare@screen-gallery
```

**Codex**
```
codex mcp add scrn --url https://scrn.gallery/mcp
codex mcp login scrn
npx skills add scrn-gallery/skills --skill scrn-flow-compare
```

**Любой другой агент.** `npx skills add scrn-gallery/skills` сам найдёт, куда положить скилл (Cursor, Gemini CLI и др.). Или скачайте папку скилла и дайте агенту прочитать `SKILL.md` — это обычная инструкция, скрипты лежат в `scripts/`.

## Как пользоваться
Опишите задачу словами:

> Найди в Screen Gallery все сценарии с рецептами у доставок продуктов. Сравни по шагам, у кого какая фишка, и собери PDF.

Дальше правьте как с дизайнером: «убери цены», «покажи кнопку в кадре», «переделай вывод».

## Лицензия
Код — MIT. Шрифт Inter — SIL Open Font License (`assets/fonts/OFL.txt`). Экраны приложений принадлежат их владельцам и берутся из каталога Screen Gallery по подписке.
