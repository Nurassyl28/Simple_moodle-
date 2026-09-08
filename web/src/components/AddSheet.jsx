import { useState } from "react";
import { X } from "lucide-react";
import { addDays, iso, pretty } from "../dates";

/**
 * Лист добавления и редактирования задачи.
 *
 * Подсказка «следующая пара по предмету» перенесена из трекера: чаще всего
 * домашку задают к следующей паре, и это избавляет от возни с календарём.
 */
export default function AddSheet({ initial, subjects, timetable, onClose, onSave }) {
  const [text, setText] = useState(initial?.text || "");
  const [subject, setSubject] = useState(initial?.subject || "");
  const [due, setDue] = useState(initial?.due || "");
  const today = new Date();

  const nextClassFor = (name) => {
    const days = new Set(timetable.filter((c) => c.name === name).map((c) => c.day));
    if (!days.size) return null;
    for (let offset = 1; offset <= 14; offset++) {
      const candidate = addDays(today, offset);
      if (days.has((candidate.getDay() + 6) % 7)) return iso(candidate);
    }
    return null;
  };

  const suggestion = subject ? nextClassFor(subject) : null;

  const submit = () => {
    if (!text.trim()) return;
    onSave({
      ...(initial?.id ? { id: initial.id } : {}),
      text: text.trim(),
      subject: subject || null,
      due: due || null,
      kind: subject ? "hw" : "todo",
    });
  };

  return (
    <div className="scrim" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>{initial?.id ? "Изменить" : "Что задали?"}</h3>
          <button className="tool" onClick={onClose} aria-label="Закрыть"><X size={16} /></button>
        </div>

        <div className="label">Задание</div>
        <textarea
          className="field"
          style={{ minHeight: 80 }}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Например: задачи 1–5 из учебника"
          autoFocus
        />

        <div className="label">Предмет</div>
        <div className="chips">
          <button className={`chip${subject ? " dim" : " on"}`} onClick={() => setSubject("")}>
            без предмета
          </button>
          {subjects.map((name) => (
            <button
              key={name}
              className={`chip${subject === name ? " on" : ""}`}
              onClick={() => setSubject(name)}
            >
              {name}
            </button>
          ))}
        </div>

        <div className="label">Когда сдавать</div>
        <div className="chips">
          <button className={`chip${due === iso(today) ? " on" : ""}`} onClick={() => setDue(iso(today))}>
            сегодня
          </button>
          <button
            className={`chip${due === iso(addDays(today, 1)) ? " on" : ""}`}
            onClick={() => setDue(iso(addDays(today, 1)))}
          >
            завтра
          </button>
          {suggestion && (
            <button className={`chip${due === suggestion ? " on" : ""}`} onClick={() => setDue(suggestion)}>
              к паре · {pretty(suggestion)}
            </button>
          )}
          <button className={`chip${!due ? " on" : " dim"}`} onClick={() => setDue("")}>
            без даты
          </button>
        </div>
        <input
          className="field"
          style={{ marginTop: 10 }}
          type="date"
          value={due}
          onChange={(e) => setDue(e.target.value)}
        />

        <button className="save" disabled={!text.trim()} onClick={submit}>
          Сохранить
        </button>
      </div>
    </div>
  );
}
