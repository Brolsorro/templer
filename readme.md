## Руководство для templer.py

Для Linux: `python3`

Для Windows: `python`

### Пример команды

```
python .\templer.py --os alt8 -tl .\templates -rt result
OR
python3 .\templer.py --os alt8 -tl .\templates -rt result
```

### Узнать о дополнительных функциях

```
python .\templer.py --help
OR
python3 .\templer.py --help
```

### Формат переменной для поддержки шаблонизации

`{{ПЕРЕМЕННАЯ}}` - формат переменной для включения в шаблон

```
Какой-то текст
Какой-то текст{{ПЕРЕМЕННАЯ}}
Какой-то текст
{{ПЕРЕМЕННАЯ}}

```

**!!!Внимание:** Для использования пользовательских переменных внутри файла-указателя (pointer.yaml) используется тот же формат, однако замена на значение только **inline**

### Команда для запуска тестов

```
python .\tests.py
OR
python3 .\tests.py
```
