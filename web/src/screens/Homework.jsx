import { useEffect, useState } from "react";
import { AlertCircle, DownloadCloud, Plus, Undo2 } from "lucide-react";
import { api } from "../api";
import { DAYS_RU, MONTHS_RU, dayIndex, pretty } from "../dates";
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
export default function Homework({ timetable, onNeedTimetable }) {
  const [groups, setGroups] = useState(null);
  const [error, setError] = useState("");
  const [sheet, setSheet] = useState(null);
  const [editing, setEditing] = useState(null);
  const [showDone, setShowDone] = useState(false);
  const [undo, setUndo] = useState(null);

  const load = async () => {
    try {
      setGroups(await api.grouped());
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

  const importDeadlines = async () => {
    try {
      const res = await api.importDeadlines();
      setError(res.added || res.updated ? "" : "Новых дедлайнов в Moodle нет");
      load();
    } catch {
      setError("Moodle не отдал дедлайны");
    }
  };

  if (!groups) return <p className="loading">Открываю тетрадь…</p>;

  const now = new Date();
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
      <div className="top">
        <div>
          <h1>{DAYS_RU[dayIndex(now)]}, {now.getDate()} {MONTHS_RU[now.getMonth()]}</h1>
          <div className="count">
            сегодня <b>{groups.due_today.length}</b> · завтра <b>{groups.due_tomorrow.length}</b>
            {groups.overdue.length > 0 && (
              <> · <b style={{ color: "#C0392B" }}>просрочено {groups.overdue.length}</b></>
            )}
          </div>
        </div>
        <div className="tools">
          <button className="tool" onClick={importDeadlines} title="Забрать дедлайны из Moodle">
            <DownloadCloud size={16} />
          </button>
          <button className="tool" onClick={() => setSheet("import")} title="Импорт списком">
            <Plus size={16} />
          </button>
        </div>
      </div>

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
          Пусто. Нажми <b>+</b>, чтобы записать домашку, или забери дедлайны из Moodle.
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
        />
      )}
      {sheet === "import" && (
        <ImportSheet onClose={() => setSheet(null)} onDone={load} />
      )}
      {subjects.length === 0 && onNeedTimetable && (
        <button className="linkbtn" style={{ marginTop: 20 }} onClick={onNeedTimetable}>
          Заполнить расписание — тогда появятся предметы и подсказки по датам
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
