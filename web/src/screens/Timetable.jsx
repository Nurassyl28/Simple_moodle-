import { useState } from "react";
import { MapPin, Trash2 } from "lucide-react";
import { api } from "../api";
import { DAYS_RU } from "../dates";

/** Расписание пар. День недели считается от понедельника, как в СДУ. */
export default function Timetable({ items, reload }) {
  const [draft, setDraft] = useState({ day: 0, name: "", time: "", room: "" });
  const [busy, setBusy] = useState(false);

  const add = async (day) => {
    if (!draft.name.trim() || !draft.time) return;
    setBusy(true);
    try {
      await api.addClass({
        day,
        name: draft.name.trim(),
        time: draft.time,
        room: draft.room.trim() || null,
      });
      setDraft({ day, name: "", time: "", room: "" });
      reload();
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id) => {
    await api.deleteClass(id);
    reload();
  };

  return (
    <>
      {DAYS_RU.map((label, day) => {
        const classes = items.filter((c) => c.day === day);
        return (
          <div className="tt-day" key={day}>
            <div className="tt-name">
              {label}
              <em>{classes.length ? `${classes.length} пар` : "нет пар"}</em>
            </div>

            {classes.map((item) => (
              <div className="tt-item" key={item.id}>
                <span className="t">{item.time.slice(0, 5)}</span>
                <span>{item.name}</span>
                {item.room && <span className="r"><MapPin size={11} /> {item.room}</span>}
                <button className="act d" onClick={() => remove(item.id)} aria-label="Убрать пару">
                  <Trash2 size={14} />
                </button>
              </div>
            ))}

            <div className="tt-form">
              <input
                placeholder="Предмет"
                value={draft.day === day ? draft.name : ""}
                onChange={(e) => setDraft({ ...draft, day, name: e.target.value })}
                style={{ flex: 2 }}
              />
              <input
                type="time"
                value={draft.day === day ? draft.time : ""}
                onChange={(e) => setDraft({ ...draft, day, time: e.target.value })}
                style={{ flex: 1 }}
              />
              <input
                placeholder="Ауд."
                value={draft.day === day ? draft.room : ""}
                onChange={(e) => setDraft({ ...draft, day, room: e.target.value })}
                style={{ width: 70 }}
              />
              <button className="chip" disabled={busy} onClick={() => add(day)}>+</button>
            </div>
          </div>
        );
      })}
    </>
  );
}
