import { Check, Pencil, Trash2 } from "lucide-react";
import { agoWord, colorFor, daysBetween, inWord, pretty } from "../dates";

/** Строка задачи. Разметка и классы — из legacy/homework-tracker.jsx. */
export default function TaskRow({ task, today, showDate, onToggle, onEdit, onDelete }) {
  const color = colorFor(task.subject);
  const late = task.due && task.due < today && !task.done;

  let meta = null;
  if (showDate && task.due) {
    const diff = daysBetween(today, task.due);
    meta = diff < 0 ? `${pretty(task.due)} · ${agoWord(-diff)}` : `${pretty(task.due)} · ${inWord(diff)}`;
  }

  return (
    <div className={`row${task.done ? " done" : ""}`}>
      <div className="edge" style={{ background: color }} />
      <button
        className={`tick${task.done ? " on" : ""}`}
        onClick={() => onToggle(task)}
        aria-label={task.done ? "Вернуть в работу" : "Отметить сделанным"}
      >
        {task.done && <Check size={13} strokeWidth={3} />}
      </button>

      <button className="body" onClick={() => onEdit(task)}>
        {task.subject && (
          <div className="subj" style={{ color }}>{task.subject}</div>
        )}
        <div className="txt">{task.text}</div>
        {meta && <div className={`meta${late ? " late" : ""}`}>{meta}</div>}
        {task.source === "moodle" && <div className="meta">из Moodle</div>}
      </button>

      <div className="acts">
        <button className="act" onClick={() => onEdit(task)} aria-label="Изменить">
          <Pencil size={15} />
        </button>
        <button className="act d" onClick={() => onDelete(task)} aria-label="Удалить">
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
}
