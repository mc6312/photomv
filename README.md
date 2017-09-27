# PHOTOMV

## НАЗНАЧЕНИЕ

Поиск в каталоге-источнике изображений и видеофайлов, их перемещение
(или копирование) в каталог-приемник.

Режим (копирование или перемещение) определяется именем исполняемого
файла.

Если он называется photomv - файлы перемещаются, если photocp - копируются.
В прочих случаях выдаётся сообщение об ошибке.

Т.е. можно создать символическую ссылку с именем photocp на файл photomv.

Имя файла настроек _не зависит_ от имени скрипта (см. раздел
"Конфигурация").

## ЧТО ТРЕБУЕТ ДЛЯ РАБОТЫ

- Linux (или другую ОС, в которой заработает нижеперечисленное)
- Python 3.3 или новее
- модули поддержки gi.repository.GExiv2

## КОНФИГУРАЦИЯ

Все параметры задаются в файле settings.ini (если он существует).

Программа ищет файл настроек в следующих каталогах (в порядке очерёдности):

1. Каталог, где расположена сама программа.
2. $HOME/.config/photomv/

При отсутствии файла настроек программа создает в каталоге из п.2 файл
со значениями по умолчанию, сообщает об этом и прекращает работу.

## КАК РАБОТАЕТ

Каталог-источник обходится рекурсивно, файлы поддерживаемых форматов
из него помещаются в подкаталоги каталога-приемника.

Имена подкаталогов и новые имена файлов задаются шаблонами из файла
настроек (см. соотв. разделы README).

Значения, подставляемые в поля шаблонов, берутся из полей EXIF исходного
файла, если они там есть, или, по возможности, из других метаданных файла.

Если в каталоге-приемнике уже есть файл с таким именем, поведение
программы зависит от параметра if-exists файла настроек.

## ФАЙЛ НАСТРОЕК

Файл настроек должен содержать две обязательные секции - __paths__ и
__options__, и может содержать необязательные - __templates__ и
__aliases__.

#### Секция paths

Параметры:

##### src-dirs

Должен быть указан один или несколько исходных каталогов, разделяемых
двоеточиями.

Пример: _/media/username/NIKON D7100/DCIM:/media/username/CANON 5D/DCIM_

В примере - пути к каталогам RAW-файлов примонтированных флэш-карт,
отформатированных средствами соотв. фотокамер.

##### dest-dir

Каталог назначения. Должен существовать на момент запуска программы.
Подкаталоги создаются при перемещении (копировании) файлов на основе
шаблонов.

Подкаталог __всегда__ создаётся внутри каталога назначения.

#### Секция options

Параметры:

##### if-exists

Задаёт поведение в ситуации, когда файл с таким же именем уже есть.

Значения:

- **s[kip]** - файл не копируется;
- **r[ename]** - к имени нового файла будет добавлен цифровой суффикс
вида "-NN" (режим по умолчанию);
- **o[verwrite]** - имеющийся файл будет перезаписан.

#### Секция templates

Необязательная секция; содержит шаблоны для новых имен файлов
и подкаталогов.

Названия параметров в этой секции:

- \* - в значении этого параметра указывается общий шаблон;
  если общий шаблон не задан, вместо него будет использоваться
  внутренний общий шаблон программы
- _имя модели камеры_ - если название этого параметра соответствует
значению поля Exif.Image.Model из исходного файла, применяется
индивидуальный шаблон камеры; сравнение значения из EXIF с названием
параметра - регистро-независимое

Если секция __templates__ отсутствует в файле настроек, ко всем файлам
применяется внутренний общий шаблон программы.

Имя подкаталога (подкаталогов) и новое имя файла задаётся в одной строке
шаблона (т.е. она может содержать символы-разделители путей).

#### Секция aliases

Необязательная секция; содержит сокращенные имена моделей камер
(для макроса ${alias} шаблонов).

Имена параметров в этой секции - названия моделей камер (как в
поле Exif.Image.Model), а значения - сокращённые имена.

Имена параметров - регистро-независимые.

Пример:

```
NIKON D70 = nd70
Canon EOS 5D Mark III = c5d3
```

## ШАБЛОНЫ

Шаблон представляет собой строку, содержащую макросы подстановки
(текст в фигурных скобках "{}"), разделители путей ("/") и/или
произвольный текст.

Символы, недопустимые в именах файлов, автоматически заменяются
символом подчёркивания ("\_").

Шаблон не должен содержать расширения - оно __всегда__ берётся из
исходного имени файла и приводится к нижнему регистру.

Внутренний общий шаблон программы, используемый при отсутствии
других шаблонов:

```
{year}/{month}/{day}/{type}{year}{month}{day}_{number}/raw
```

### Макросы подстановки

Формат макроса - {имя}. Имена регистро-независимые, могут быть
указаны в полном или сокращенном виде.

Для вставки в шаблон символов фигурных скобок как есть - их следует
удваивать.

Значения полей берутся из EXIF исходного файла (если есть), из
имён и метаданных файлов в ФС (если есть). Отсутствующие
значения заменяются символом подчёркивания ("_").

#### {y[ear]}, {mon[th]}, {d[ay]}, {h[our]}, {m[inute]}

Год (с тысячелетием), месяц, день, час и минута создания файла
соответственно.

При наличии в файле EXIF - берутся оттуда, иначе - из даты последнего
изменения файла в ФС.

#### {model}

Название модели камеры (из Exif.Image.Model).

#### {a[lias]}

Сокращённое имя модели камеры.

Берётся соотв. значение из секции __aliases__ файла настроек.

#### {p[refix]}

Префикс исходного имени файла (например, для DSCN0666.NEF - "DSCN").

#### {n[umber]}

Номер из исходного имени файла (например, для DSCN0666.NEF - "0666").

#### {t[ype]}

Тип исходного файла - p (photo) или v (video).

Определяется по расширению.
