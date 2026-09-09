import { useEffect, useState } from "react";
import { AlertCircle, Plus, Undo2 } from "lucide-react";
import { api } from "../api";
import { pretty } from "../dates";
import AddSheet from "../components/AddSheet";
import ImportSheet from "../components/ImportSheet";
import TaskRow from "../components/TaskRow";

/**
 * Домашка и дела.
 *
 * Группировку теперь считает бэкенд (/api/tasks/grouped): у него правильный
 * часовой пояс студента, и одна и та же логика не расходится между клиентами.
 * Экран только показывает готовые корзины.
 */
export default function Homework({ timetable, onSummary, onNeedTimetable }) {
  const [groups, setGroups] = useState(null);
  const [error, setError] = useState("");
  const [sheet, setSheet] = useState(null);
  const [editing, setEditing] = useState(null);
  const [showDone, setShowDone] = useState(false);
  const [undo, setUndo] = useState(null);

  const load = async () => {
    try {
      const data = await api.grouped();
      setGroups(data);
      // Счётчики живут в общей шапке приложения, а данные приходят сюда.
      onSummary?.({
        today: data.due_today.length,
        tomorrow: data.due_tomorrow.length,
        overdue: data.overdue.length,
      });
      setError("");
    } catch {
      setError("Не получилось загрузить задачи");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggle = async (task) => {
    // Отмечаем сразу, не дожидаясь сети: щелчок должен ощущаться мгновенно.
    setGroups((prev) => reflect(prev, task.id, { done: !task.done }));
    try {
      await api.patchTask(task.id, { done: !task.done });
    } finally {
      load();
    }
  };

  const remove = async (task) => {
    await api.deleteTask(task.id);
    // Отменить нельзя молча: показываем, что именно исчезло, и даём вернуть.
    setUndo(task);
    setTimeout(() => setUndo((u) => (u?.id === task.id ? null : u)), 7000);
    load();
  };

  const restore = async () => {
    if (!undo) return;
    await api.createTask({ text: undo.text, subject: undo.subject, due: undo.due, kind: undo.kind });
    setUndo(null);
    load();
  };

  const save = async (task) => {
    if (task.id) {
      const { id, ...changes } = task;
      await api.patchTask(id, changes);
    } else {
      await api.createTask(task);
    }
    setSheet(null);
    setEditing(null);
    load();
  };

  if (!groups) return <p className="loading">Открываю тетрадь…</p>;

  const subjects = [
    ...new Set([
      ...timetable.map((c) => c.name),
      ...[...groups.overdue, ...groups.due_today, ...groups.due_tomorrow, ...groups.undated]
        .map((t) => t.subject)
        .filter(Boolean),
    ]),
  ];

  const openEditor = (task) => {
    setEditing(task);
    setSheet("add");
  };
  const rowProps = { today: groups.today, onToggle: toggle, onEdit: openEditor, onDelete: remove };

  return (
    <>
      {error && <div className="banner"><AlertCircle size={15} /> {error}</div>}

      <Section title="Просрочено" items={groups.overdue} showDate {...rowProps} />
      <Section title="Сегодня" items={groups.due_today} {...rowProps} />
      <Section title="Завтра" items={groups.due_tomorrow} {...rowProps} />

      {groups.later.length > 0 && (
        <div className="sect">
          <div className="sect-head small"><h2>Дальше</h2></div>
          {groups.later.map((group) => (
            <div key={group.due}>
              <div className="datehead"><b>{pretty(group.due)}</b></div>
              <div className="card">
                {group.items.map((task) => <TaskRow key={task.id} task={task} {...rowProps} />)}
              </div>
            </div>
          ))}
        </div>
      )}

      <Section title="Без даты" items={groups.undated} small {...rowProps} />

      {groups.done.length > 0 && (
        <div className="sect">
          <button className={`fold${showDone ? " open" : ""}`} onClick={() => setShowDone(!showDone)}>
            Сделано · {groups.done.length}
          </button>
          {showDone && (
            <div className="card">
              {groups.done.map((task) => <TaskRow key={task.id} task={task} {...rowProps} />)}
            </div>
          )}
        </div>
      )}

      {isEmpty(groups) && (
        <div className="empty">
          Пока ничего не записано.<br />
          Нажми <b>+</b> внизу справа или перенеси дедлайны на вкладке «Дедлайны».
        </div>
      )}

      <button className="fab" onClick={() => { setEditing(null); setSheet("add"); }} aria-label="Добавить">
        <Plus size={24} />
      </button>

      {undo && (
        <div className="undo">
          <span>Удалено: {undo.text.slice(0, 30)}</span>
          <button onClick={restore}><Undo2 size={15} /> Вернуть</button>
        </div>
      )}

      {sheet === "add" && (
        <AddSheet
          initial={editing}
          subjects={subjects}
          timetable={timetable}
          onClose={() => { setSheet(null); setEditing(null); }}
          onSave={save}
          onImport={() => { setEditing(null); setSheet("import"); }}
        />
      )}
      {sheet === "import" && (
        <ImportSheet onClose={() => setSheet(null)} onDone={load} />
      )}
      {subjects.length === 0 && onNeedTimetable && (
        <button className="linkbtn" style={{ marginTop: 24 }} onClick={onNeedTimetable}>
          Заполнить расписание — появятся предметы и подсказка «к паре»
        </button>
      )}
    </>
  );
}

function Section({ title, items, showDate, small, ...rowProps }) {
  if (!items.length) return null;
  return (
    <div className="sect">
      <div className={`sect-head${small ? " small" : ""}`}>
        <h2 className={small ? "" : "mark"}><span>{title}</span></h2>
      </div>
      <div className="card">
        {items.map((task) => (
          <TaskRow key={task.id} task={task} showDate={showDate} {...rowProps} />
        ))}
      </div>
    </div>
  );
}

/** Локальная правка до ответа сервера — чтобы галочка не «залипала». */
function reflect(groups, id, changes) {
  if (!groups) return groups;
  const patch = (list) => list.map((t) => (t.id === id ? { ...t, ...changes } : t));
  return {
    ...groups,
    overdue: patch(groups.overdue),
    due_today: patch(groups.due_today),
    due_tomorrow: patch(groups.due_tomorrow),
    undated: patch(groups.undated),
    done: patch(groups.done),
    later: groups.later.map((g) => ({ ...g, items: patch(g.items) })),
  };
}

const isEmpty = (g) =>
  !g.overdue.length && !g.due_today.length && !g.due_tomorrow.length &&
  !g.later.length && !g.undated.length && !g.done.length;
