import { useCallback, useEffect, useState } from "react";
import { CalendarClock, CalendarDays, FileText, GraduationCap, NotebookPen } from "lucide-react";
import { api } from "./api";
import Login from "./Login";
import ProfileSheet from "./components/ProfileSheet";
import Homework from "./screens/Homework";
import Grades from "./screens/Grades";
import Files from "./screens/Files";
import Deadlines from "./screens/Deadlines";
import Timetable from "./screens/Timetable";
import { DAYS_RU, MONTHS_RU, dayIndex } from "./dates";

const TABS = [
  { id: "hw", label: "Домашка", icon: NotebookPen },
  { id: "grades", label: "Оценки", icon: GraduationCap, sub: "Из Moodle" },
  { id: "files", label: "Файлы", icon: FileText, sub: "Материалы курсов" },
  { id: "deadlines", label: "Дедлайны", icon: CalendarClock, sub: "Календарь Moodle" },
  { id: "timetable", label: "Пары", icon: CalendarDays, sub: "Своё расписание" },
];

/** Инициалы для кнопки профиля: «Nurassyl Bazarbay» → «NB». */
const initials = (name) =>
  (name || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");

export default function App() {
  const [me, setMe] = useState(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState("hw");
  const [timetable, setTimetable] = useState([]);
  const [summary, setSummary] = useState(null);
  const [profileOpen, setProfileOpen] = useState(false);

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

  const forget = () => {
    setMe(null);
    setTimetable([]);
    setProfileOpen(false);
  };

  const logout = async () => {
    await api.logout().catch(() => {});
    forget();
  };

  /* SECURITY.md требует дать студенту удалить аккаунт и все данные. */
  const removeAccount = async () => {
    const sure = window.confirm(
      "Удалить аккаунт? Токен Moodle, задачи и расписание будут стёрты без возможности вернуть.",
    );
    if (!sure) return;
    await api.deleteAccount().catch(() => {});
    forget();
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

  const active = TABS.find((t) => t.id === tab);
  const now = new Date();

  /* На «Домашке» заголовок — сегодняшняя дата: она полезнее слова «Домашка». */
  const title =
    tab === "hw" ? `${DAYS_RU[dayIndex(now)]}, ${now.getDate()} ${MONTHS_RU[now.getMonth()]}` : active.label;

  return (
    <div className="hw">
      <div className="wrap">
        <div className="head">
          <div>
            <h1>{title}</h1>
            <div className="sub">
              {tab === "hw" && summary ? (
                <>
                  сегодня <b>{summary.today}</b> · завтра <b>{summary.tomorrow}</b>
                  {summary.overdue > 0 && <> · <span className="bad">просрочено {summary.overdue}</span></>}
                </>
              ) : (
                active.sub
              )}
            </div>
          </div>
          <button className="avatar" onClick={() => setProfileOpen(true)} title={me.fullname}>
            {initials(me.fullname)}
          </button>
        </div>

        {tab === "hw" && (
          <Homework
            timetable={timetable}
            onSummary={setSummary}
            onNeedTimetable={() => setTab("timetable")}
          />
        )}
        {tab === "grades" && <Grades />}
        {tab === "files" && <Files />}
        {tab === "deadlines" && <Deadlines />}
        {tab === "timetable" && <Timetable items={timetable} reload={loadTimetable} />}
      </div>

      <div className="nav">
        <div className="nav-inner">
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

      {profileOpen && (
        <ProfileSheet
          fullname={me.fullname}
          onClose={() => setProfileOpen(false)}
          onLogout={logout}
          onDelete={removeAccount}
        />
      )}
    </div>
  );
}
