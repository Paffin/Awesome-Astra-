# Astra Codex Skills

Два компактных Skill для GPT-6 Astra в Codex: максимум полезного контекста, минимум инструкционного шума.

- `astra-code` — реализация, отладка, рефакторинг, ревью и архитектурные решения с точечным чтением репозитория и соразмерной проверкой.
- `astra-repo-audit` — аудит и сокращение `AGENTS.md`, Skills и настроек Codex без удаления реальных ограничений безопасности.

Репозиторий оформлен как переносимый [Agent Plugin](https://developers.openai.com/plugins/build/plugins), а каждый Skill совместим с открытым форматом Agent Skills.

## Почему здесь мало инструкций

Astra хуже работает не от недостатка длинных промптов, а от лишнего и конфликтующего контекста. Поэтому пакет использует два непересекающихся Skill, короткий роутер, один подгружаемый сценарий на задачу, локализацию нужного кода и проверку, соразмерную риску изменения.

Мы не заявляем экономию токенов, ускорение или рост качества без парного замера. Методика измерения находится в [EVALUATION.md](EVALUATION.md), а связь решений с исследованиями — в [RESEARCH.md](RESEARCH.md).

## Установка

Можно попросить Codex установить оба Skill через `$skill-installer` из папки:

```text
https://github.com/Paffin/Awesome-Astra-/tree/main/skills
```

Локальная установка:

```bash
git clone https://github.com/Paffin/Awesome-Astra-.git
cd Awesome-Astra-
python3 scripts/install.py
```

По умолчанию файлы копируются в `$HOME/.agents/skills`. Существующие Skills не перезаписываются без `--force`; при принудительном обновлении сначала создаётся резервная копия.

```bash
python3 scripts/install.py --skill astra-code
python3 scripts/install.py --dest /path/to/repo/.agents/skills
```

## Использование

```text
$astra-code исправь гонку в queue worker и проверь регрессию.
$astra-code проведи ревью этой ветки относительно main.
$astra-repo-audit только проверь AGENTS.md и Skills, файлы не меняй.
$astra-repo-audit сократи лишние инструкции и проверь результат.
```

## Проверка проекта

Зависимости не нужны:

```bash
python3 tools/validate.py
python3 -m unittest discover -s tests -v
```

Лицензия: [MIT](LICENSE).
