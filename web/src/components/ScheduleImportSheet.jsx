import { useState } from "react";
import { AlertCircle, X } from "lucide-react";
import { api } from "../api";
import { DAYS_RU } from "../dates";

/**
 * Импорт расписания из портала СДУ.
 *
 * Основной способ — вставка скопированной таблицы. Расписания пар в Moodle нет,
 * а страница портала это обычная таблица: при копировании в буфер попадает её
 * разметка, где столбец — день, а строка — время. Разбор получается точным,
 * мгновенным и бесплатным, и ничего не уходит во внешние сервисы.
 *
 * Скриншот оставлен запасным путём — на случай, когда скопировать не выходит.
 *
 * Распознанное показывается на подтверждение, а не сохраняется сразу: молча
 * переписать чужое расписание хуже, чем показать и спросить.
 */
export default function ScheduleImportSheet({ onClose, onDone }) {
  const [classes, setClasses] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("paste");

  const accept = (result) => {
    setError(result.classes.length ? "" : "Занятий в таблице не нашлось.");
    setClasses(result.classes);
  };

  const onPaste = async (event) => {
    // text/html сохраняет структуру таблицы; из простого текста уже не понять,
    // в каком столбце стояла ячейка, а значит и какой это день.
    const html = event.clipboardData.getData("text/html");
    event.preventDefault();

    if (!html) {
      setError("Скопируй саму таблицу со страницы, а не текст из неё.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      accept(await api.parseScheduleHtml(html));
    } catch (err) {
      setError(
        err.status === 422
          ? "В скопированном нет таблицы расписания. Выдели страницу целиком."
          : "Не получилось разобрать таблицу",
      );
    } finally {
      setBusy(false);
    }
  };

  const pickImage = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setBusy(true);
    setError("");
    try {
      accept(await api.parseScheduleImage(file));
    } catch (err) {
      setError(
        err.status === 503
          ? "Распознавание картинок не настроено. Вставь таблицу — это работает всегда."
          : err.message,
      );
    } finally {
      setBusy(false);
    }
  };

  const save = async (replace) => {
    setBusy(true);
    try {
      await api.saveTimetable(classes, replace);
      onDone();
      onClose();
    } catch {
      setError("Не получилось сохранить");
    } finally {
      setBusy(false);
    }
  };

  const byDay = (classes || []).reduce((acc, item) => {
    (acc[item.day] ||= []).push(item);
    return acc;
  }, {});

  return (
    <div className="scrim" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>Расписание из портала</h3>
          <button className="tool" onClick={onClose} aria-label="Закрыть"><X size={16} /></button>
        </div>

        {!classes && mode === "paste" && (
          <>
            <p className="hint">
              Открой в портале СДУ страницу <b>Course Schedule</b>, выдели её целиком
              (Cmd+A или Ctrl+A), скопируй (Cmd+C) и вставь сюда (Cmd+V). Занятия
              расставятся по дням сами.
            </p>
            <textarea
              className="field"
              style={{ minHeight: 110 }}
              placeholder={busy ? "Разбираю таблицу…" : "Вставь сюда скопированное расписание"}
              onPaste={onPaste}
              onChange={() => {}}
              value=""
              disabled={busy}
              autoFocus
            />
            <button
              className="linkbtn"
              style={{ display: "block", margin: "16px auto 0" }}
              onClick={() => { setMode("image"); setError(""); }}
            >
              не получается скопировать — загрузить скриншот
            </button>
          </>
        )}

        {!classes && mode === "image" && (
          <>
            <p className="hint">
              Загрузи скриншот таблицы Course Schedule. Этот способ нужен, только
              если скопировать таблицу не выходит.
            </p>
            {/* SECURITY.md: единственное место, где данные студента уходят
                наружу, — говорим об этом до загрузки, а не после. */}
            <div className="banner">
              <AlertCircle size={15} />
              Картинка отправится в сервис распознавания Anthropic. Мы её не храним.
            </div>
            <label className="save" style={{ display: "block", textAlign: "center", cursor: "pointer" }}>
              {busy ? "Читаю картинку…" : "Выбрать картинку"}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={pickImage}
                disabled={busy}
                hidden
              />
            </label>
            <button
              className="linkbtn"
              style={{ display: "block", margin: "16px auto 0" }}
              onClick={() => { setMode("paste"); setError(""); }}
            >
              вернуться к вставке таблицы
            </button>
          </>
        )}

        {classes && classes.length > 0 && (
          <>
            <p className="hint">
              Нашлось занятий: <b>{classes.length}</b>. Проверь и сохрани.
            </p>
            {Object.entries(byDay).map(([day, items]) => (
              <div key={day}>
                <div className="group-title">{DAYS_RU[day]}</div>
                <div className="card">
                  {items.map((item, i) => (
                    <div className="tt-item" key={i} style={{ padding: "8px 12px" }}>
                      <span className="t">{item.time.slice(0, 5)}</span>
                      <span>{item.name}</span>
                      {item.room && <span className="r">{item.room}</span>}
                    </div>
                  ))}
                </div>
              </div>
            ))}

            <button className="save" disabled={busy} onClick={() => save(true)}>
              Заменить моё расписание
            </button>
            <button
              className="linkbtn"
              style={{ display: "block", margin: "14px auto 0" }}
              disabled={busy}
              onClick={() => save(false)}
            >
              или добавить к тому, что есть
            </button>
          </>
        )}

        {error && <div className="result bad">{error}</div>}
      </div>
    </div>
  );
}
