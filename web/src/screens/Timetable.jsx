import { useState } from "react";
import { ImagePlus, MapPin, Plus, Trash2, X } from "lucide-react";
import { api } from "../api";
import { DAYS_RU } from "../dates";
import ScheduleImportSheet from "../components/ScheduleImportSheet";

const EMPTY = { name: "", time: "", room: "" };

/**
 * Расписание пар. День недели считается от понедельника, как в СДУ.
 *
 * Раньше форма добавления была раскрыта под каждым из семи дней сразу — экран
 * выглядел стеной одинаковых полей. Теперь форма открывается по кнопке того дня,
 * куда добавляют.
 */
export default function Timetable({ items, reload }) {
  const [openDay, setOpenDay] = useState(null);
  const [importing, setImporting] = useState(false);
  const [draft, setDraft] = useState(EMPTY);
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
      setDraft(EMPTY);
      setOpenDay(null);
      reload();
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id) => {
    await api.deleteClass(id);
    reload();
  };

  const open = (day) => {
    setOpenDay(day);
    setDraft(EMPTY);
  };

  return (
    <>
      {/* Заполнять расписание руками — семь дней и десяток пар. Вставка
          таблицы из портала делает это за один шаг. */}
      <button
        className="daybtn"
        style={{ marginBottom: 18, display: "flex", alignItems: "center", gap: 8 }}
        onClick={() => setImporting(true)}
      >
        <ImagePlus size={15} /> Заполнить из портала СДУ
      </button>

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

            {openDay === day ? (
              <div className="tt-form">
                <input
                  placeholder="Предмет"
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                  style={{ flex: 2 }}
                  autoFocus
                />
                <input
                  type="time"
                  value={draft.time}
                  onChange={(e) => setDraft({ ...draft, time: e.target.value })}
                  style={{ flex: 1 }}
                />
                <input
                  placeholder="Ауд."
                  value={draft.room}
                  onChange={(e) => setDraft({ ...draft, room: e.target.value })}
                  style={{ width: 66 }}
                />
                <button
                  className="chip on"
                  disabled={busy || !draft.name.trim() || !draft.time}
                  onClick={() => add(day)}
                >
                  <Plus size={14} />
                </button>
                <button className="tool" onClick={() => setOpenDay(null)} aria-label="Отменить">
                  <X size={14} />
                </button>
              </div>
            ) : (
              <button className="daybtn" onClick={() => open(day)}>
                + добавить пару
              </button>
            )}
          </div>
        );
      })}

      {importing && (
        <ScheduleImportSheet onClose={() => setImporting(false)} onDone={reload} />
      )}
    </>
  );
}
