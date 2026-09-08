import { useCallback, useEffect, useState } from "react";
import { CalendarDays, FileText, GraduationCap, NotebookPen, CalendarClock } from "lucide-react";
import { api } from "./api";
import Login from "./Login";
import Homework from "./screens/Homework";
import Grades from "./screens/Grades";
import Files from "./screens/Files";
import Deadlines from "./screens/Deadlines";
import Timetable from "./screens/Timetable";

const TABS = [
  { id: "hw", label: "Домашка", icon: NotebookPen },
  { id: "grades", label: "Оценки", icon: GraduationCap },
  { id: "files", label: "Файлы", icon: FileText },
  { id: "deadlines", label: "Дедлайны", icon: CalendarClock },
  { id: "timetable", label: "Пары", icon: CalendarDays },
];

export default function App() {
  const [me, setMe] = useState(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState("hw");
  const [timetable, setTimetable] = useState([]);

  const loadTimetable = useCallback(() => {
    api.timetable().then(setTimetable).catch(() => setTimetable([]));
  }, []);

  useEffect(() => {
    // Cookie httpOnly скрипту не видна, поэтому «вошли или нет» узнаём запросом.
    api.me()
      .then((data) => { setMe(data); loadTimetable(); })
      .catch(() => setMe(null))
      .finally(() => setChecking(false));
  }, [loadTimetable]);

  const logout = async () => {
    await api.logout().catch(() => {});
    setMe(null);
    setTimetable([]);
  };

  if (checking) {
    return <div className="hw"><div className="wrap"><p className="loading">Секунду…</p></div></div>;
  }

  if (!me) {
    return (
      <div className="hw">
        <Login onDone={() => window.location.reload()} />
      </div>
    );
  }

  return (
    <div className="hw">
      <div className="wrap">
        <div className="tabs">
          {TABS.map((t) => (
            <button key={t.id} className={`tab${tab === t.id ? " on" : ""}`} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {tab === "hw" && <Homework timetable={timetable} onNeedTimetable={() => setTab("timetable")} />}
        {tab === "grades" && <Grades />}
        {tab === "files" && <Files />}
        {tab === "deadlines" && <Deadlines />}
        {tab === "timetable" && <Timetable items={timetable} reload={loadTimetable} />}

        <div className="danger">
          <button className="linkbtn" onClick={logout}>Выйти ({me.fullname})</button>
        </div>
      </div>

      <div className="nav">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button key={t.id} className={tab === t.id ? "on" : ""} onClick={() => setTab(t.id)}>
              <Icon size={18} />
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
